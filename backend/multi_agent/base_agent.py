from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backend.agent.browser_session import BrowserSession, BrowserSessionManager
from backend.agent.live_reasoning.engine import LiveReasoningEngine
from backend.agent.services.stability_service import StabilityService
from backend.events.bus import ExecutionEventBus, event_bus
from backend.events.schemas import ExecutionEvent, ExecutionEventType
from backend.multi_agent.coverage import WorkflowCoverageEngine
from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding, MultiAgentRunRequest
from backend.multi_agent.navigation_graph import NavigationGraphEngine
from backend.multi_agent.session_sync import BrowserStateSnapshot, capture_browser_state, restore_session_storage
from backend.multi_agent.shared_memory import SharedAgentMemory


@dataclass(slots=True)
class AgentRuntimeContext:
    run_id: str
    request: MultiAgentRunRequest
    shared_memory: SharedAgentMemory
    navigation_graph: NavigationGraphEngine
    coverage: WorkflowCoverageEngine
    browser_manager: BrowserSessionManager
    bus: ExecutionEventBus = event_bus
    artifact_root: str = "artifacts"
    shared_snapshot: Optional[BrowserStateSnapshot] = None
    run_started_at: datetime = field(default_factory=datetime.utcnow)


class BaseMultiAgent(ABC):
    name: str = "BaseMultiAgent"
    confidence_floor: float = 0.5
    requires_browser: bool = True
    recovery_limit: int = 1

    def __init__(self) -> None:
        self.reasoning = LiveReasoningEngine()
        self.stability = StabilityService()

    async def run(self, context: AgentRuntimeContext) -> AgentExecutionResult:
        await self._publish(context, ExecutionEventType.RUN_STATUS, f"{self.name} started", phase="started")
        session: Optional[BrowserSession] = None
        started_at = datetime.utcnow()
        try:
            session = await self._open_session(context)
            plan = await self.plan(context, session)
            await self._publish(context, ExecutionEventType.AGENT_REASONING, plan.get("message", f"Planning {self.name}"), plan=plan)
            result = await self.execute(context, session, plan)
            result.started_at = started_at
            result.completed_at = datetime.utcnow()
            if result.confidence < self.confidence_floor:
                result.status = result.status if result.status != "completed" else "completed_with_low_confidence"
            result.report = await self.report(context, result)
            await context.shared_memory.record_agent_result(result)
            await self._record_state(context, session, result)
            await self._publish(context, ExecutionEventType.RUN_STATUS, f"{self.name} completed", status=result.status, confidence=result.confidence)
            return result
        except Exception as exc:
            recovered = await self.recover(context, session, exc)
            recovered.started_at = started_at
            recovered.completed_at = datetime.utcnow()
            recovered.report = await self.report(context, recovered)
            await context.shared_memory.record_agent_result(recovered)
            await self._publish(context, ExecutionEventType.BUG_DETECTED, f"{self.name} failed", severity="high", error=str(exc))
            return recovered
        finally:
            if session is not None:
                await session.close()

    async def _open_session(self, context: AgentRuntimeContext) -> Optional[BrowserSession]:
        if not self.requires_browser:
            return None
        storage_state = context.shared_snapshot.storage_state_path if context.shared_snapshot else None
        if storage_state and not Path(storage_state).exists():
            storage_state = None
        session = await context.browser_manager.new_session(storage_state=storage_state)
        await session.page.goto(str(context.request.url), wait_until="load", timeout=45000)
        await self.stability.wait_for_stable(session.page, timeout_ms=8000)
        if context.shared_snapshot:
            await restore_session_storage(session.page, context.shared_snapshot.session_storage)
        return session

    async def _record_state(self, context: AgentRuntimeContext, session: Optional[BrowserSession], result: AgentExecutionResult) -> None:
        if session is None:
            return
        snapshot = await capture_browser_state(session, context.artifact_root, context.run_id, self.name)
        await context.shared_memory.set_storage_state_path(snapshot.storage_state_path)
        await context.shared_memory.set_session_storage(snapshot.session_storage)
        await context.shared_memory.record_workflow_state(result.run.get("workflow_state", ""))
        if result.run.get("steps"):
            await context.navigation_graph.record_run(result.run, self.name)

    async def _publish(self, context: AgentRuntimeContext, event_type: ExecutionEventType, message: str, **payload: Any) -> None:
        await context.bus.publish(
            ExecutionEvent(
                run_id=context.run_id,
                agent=self.name,
                type=event_type,
                message=message,
                payload={k: v for k, v in payload.items() if v is not None},
            )
        )

    async def plan(self, context: AgentRuntimeContext, session: Optional[BrowserSession]) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "message": f"Planning {self.name} for {context.request.goal}",
            "goal": context.request.goal,
            "url": str(context.request.url),
        }

    @abstractmethod
    async def execute(self, context: AgentRuntimeContext, session: Optional[BrowserSession], plan: Dict[str, Any]) -> AgentExecutionResult:
        raise NotImplementedError

    async def validate(self, context: AgentRuntimeContext, result: AgentExecutionResult) -> bool:
        return result.confidence >= self.confidence_floor and result.status.startswith("completed")

    async def recover(self, context: AgentRuntimeContext, session: Optional[BrowserSession], error: Exception) -> AgentExecutionResult:
        finding = MultiAgentFinding(
            agent_name=self.name,
            category="execution_failure",
            severity="high",
            message=str(error),
            root_cause="agent runtime failure",
            url=str(context.request.url),
            evidence={"exception": type(error).__name__},
        )
        await context.shared_memory.record_bug(finding)
        return AgentExecutionResult(
            agent_name=self.name,
            status="failed",
            confidence=0.0,
            summary=str(error),
            findings=[finding],
        )

    async def report(self, context: AgentRuntimeContext, result: AgentExecutionResult) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "status": result.status,
            "confidence": result.confidence,
            "summary": result.summary,
            "findings": [finding.model_dump(mode="json") for finding in result.findings],
        }
