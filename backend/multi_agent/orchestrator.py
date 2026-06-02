from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.agent.browser_session import BrowserSessionManager
from backend.events.bus import event_bus
from backend.events.schemas import ExecutionEvent, ExecutionEventType
from backend.multi_agent.agents import (
    AccessibilityAgent,
    AuthenticationAgent,
    NavigationAgent,
    PerformanceAgent,
    VisualQAAgent,
)
from backend.multi_agent.base_agent import AgentRuntimeContext
from backend.multi_agent.consensus import ConsensusValidationEngine
from backend.multi_agent.coverage import WorkflowCoverageEngine
from backend.multi_agent.models import AgentExecutionResult, MultiAgentRunRequest, UnifiedMultiAgentReport
from backend.multi_agent.navigation_graph import NavigationGraphEngine
from backend.multi_agent.reporting import build_unified_report
from backend.multi_agent.session_sync import BrowserStateSnapshot
from backend.multi_agent.shared_memory import SharedAgentMemory


@dataclass(slots=True)
class MultiAgentExecutionState:
    run_id: str
    request: MultiAgentRunRequest
    shared_memory: SharedAgentMemory
    navigation_graph: NavigationGraphEngine
    coverage: WorkflowCoverageEngine
    browser_manager: BrowserSessionManager
    bus = event_bus
    shared_snapshot: Optional[BrowserStateSnapshot] = None


class MultiAgentOrchestrator:
    def __init__(self, browser_manager: Optional[BrowserSessionManager] = None) -> None:
        self._owns_browser_manager = browser_manager is None
        self.browser_manager = browser_manager or BrowserSessionManager(headless=True)
        self.consensus_engine = ConsensusValidationEngine()
        self._agent_factories = {
            "AuthenticationAgent": AuthenticationAgent,
            "NavigationAgent": NavigationAgent,
            "AccessibilityAgent": AccessibilityAgent,
            "PerformanceAgent": PerformanceAgent,
            "VisualQAAgent": VisualQAAgent,
        }

    async def run(self, request: MultiAgentRunRequest) -> Dict[str, Any]:
        run_id = request.run_id or str(uuid.uuid4())
        shared_memory = SharedAgentMemory(run_id)
        navigation_graph = NavigationGraphEngine()
        coverage = WorkflowCoverageEngine()
        state = MultiAgentExecutionState(
            run_id=run_id,
            request=request,
            shared_memory=shared_memory,
            navigation_graph=navigation_graph,
            coverage=coverage,
            browser_manager=self.browser_manager,
        )

        try:
            await event_bus.publish(ExecutionEvent(run_id=run_id, agent="MultiAgentOrchestrator", type=ExecutionEventType.RUN_STATUS, message="multi-agent run started", payload={"goal": request.goal}))

            agents = self._build_agents(request)
            ordered_results: List[AgentExecutionResult] = []

            auth_agent = next((agent for agent in agents if agent.name == "AuthenticationAgent"), None)
            if auth_agent is not None:
                result = await self._run_agent_safe(auth_agent, state)
                ordered_results.append(result)
                await self._refresh_shared_snapshot(state)
                await self._record_result_effects(state, auth_agent.name, result)

            remaining_agents = [agent for agent in agents if agent.name != "AuthenticationAgent"]
            if request.enable_parallel:
                results = await asyncio.gather(*(self._run_agent_safe(agent, state) for agent in remaining_agents))
            else:
                results = []
                for agent in remaining_agents:
                    results.append(await self._run_agent_safe(agent, state))

            for agent, result in zip(remaining_agents, results):
                ordered_results.append(result)
                await self._record_result_effects(state, agent.name, result)

            await self._refresh_shared_snapshot(state)
            consensus = self.consensus_engine.validate(ordered_results)
            await self._emit_consensus_events(run_id, consensus)

            coverage_snapshot = await coverage.snapshot()
            navigation_snapshot = await navigation_graph.snapshot()
            shared_snapshot = await shared_memory.snapshot()
            failed_agents = [result for result in ordered_results if result.status not in {"completed", "completed_with_failures"}]
            run_status = "completed_with_failures" if failed_agents else "completed"
            if not ordered_results:
                run_status = "failed"
            report = build_unified_report(
                run_id=run_id,
                user_id=request.user_id or "",
                goal=request.goal,
                status=run_status,
                agent_results=ordered_results,
                consensus=consensus,
                shared_memory=shared_snapshot,
                navigation_graph=navigation_snapshot,
                workflow_coverage=coverage_snapshot,
            )

            await event_bus.publish(ExecutionEvent(run_id=run_id, agent="MultiAgentOrchestrator", type=ExecutionEventType.RUN_STATUS, message="multi-agent run completed", payload={"report_id": report.get("report_id")}))

            return {
                "run_id": run_id,
                "goal": request.goal,
                "status": run_status,
                "agent_results": [result.model_dump(mode="json") for result in ordered_results],
                "consensus": consensus,
                "coverage": coverage_snapshot,
                "navigation_graph": navigation_snapshot,
                "shared_memory": shared_snapshot,
                "report": report,
            }
        finally:
            if self._owns_browser_manager:
                try:
                    await self.browser_manager.shutdown()
                except Exception:
                    pass

    def _build_agents(self, request: MultiAgentRunRequest) -> List[Any]:
        agent_names = request.agent_names or [
            "AuthenticationAgent",
            "NavigationAgent",
            "AccessibilityAgent",
            "PerformanceAgent",
            "VisualQAAgent",
        ]
        agents: List[Any] = []
        for name in agent_names:
            factory = self._agent_factories.get(name)
            if factory is not None:
                agents.append(factory())
        return agents

    def _build_context(self, state: MultiAgentExecutionState) -> AgentRuntimeContext:
        return AgentRuntimeContext(
            run_id=state.run_id,
            request=state.request,
            shared_memory=state.shared_memory,
            navigation_graph=state.navigation_graph,
            coverage=state.coverage,
            browser_manager=state.browser_manager,
            bus=event_bus,
            shared_snapshot=state.shared_snapshot,
        )

    async def _refresh_shared_snapshot(self, state: MultiAgentExecutionState) -> None:
        state.shared_snapshot = BrowserStateSnapshot(**{k: v for k, v in (await state.shared_memory.snapshot()).items() if k in {"storage_state_path", "session_storage"}})

    async def _record_result_effects(self, state: MultiAgentExecutionState, agent_name: str, result: AgentExecutionResult) -> None:
        if result.run:
            await state.navigation_graph.record_run(result.run, agent_name)
            await state.coverage.record_run(result.run)
        for finding in result.findings:
            await event_bus.publish(
                ExecutionEvent(
                    run_id=state.run_id,
                    agent=agent_name,
                    type=ExecutionEventType.BUG_DETECTED,
                    message=finding.message,
                    severity=finding.severity,
                    confidence=finding.confidence,
                    url=finding.url,
                    payload=finding.model_dump(mode="json"),
                )
            )

    async def _emit_consensus_events(self, run_id: str, consensus: Dict[str, Any]) -> None:
        for item in consensus.get("consensus_findings", []):
            await event_bus.publish(
                ExecutionEvent(
                    run_id=run_id,
                    agent="ConsensusValidationEngine",
                    type=ExecutionEventType.BUG_DETECTED,
                    message=item.get("root_cause", "consensus finding"),
                    severity=item.get("severity", "medium"),
                    confidence=item.get("confidence", 0.0),
                    payload=item,
                )
            )

    async def _run_agent_safe(self, agent: Any, state: MultiAgentExecutionState) -> AgentExecutionResult:
        try:
            return await agent.run(self._build_context(state))
        except Exception as exc:
            return await agent.recover(self._build_context(state), None, exc)

