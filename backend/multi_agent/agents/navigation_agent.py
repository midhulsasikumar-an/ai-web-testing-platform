from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.agent_loop_v2 import run_agent_loop_v2
from backend.agent.browser_session import BrowserSession
from backend.multi_agent.base_agent import AgentRuntimeContext, BaseMultiAgent
from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding


class NavigationAgent(BaseMultiAgent):
    name = "NavigationAgent"
    confidence_floor = 0.55

    async def execute(self, context: AgentRuntimeContext, session: Optional[BrowserSession], plan: Dict[str, Any]) -> AgentExecutionResult:
        if session is None:
            raise RuntimeError("NavigationAgent requires a browser session")
        run_data = await run_agent_loop_v2(
            page=session.page,
            goal="explore_navigation",
            credentials=context.request.credentials,
            start_url=str(context.request.url),
            max_steps=context.request.max_steps,
            same_origin_only=True,
            signals=session.signals,
            event_bus=context.bus,
            run_id=context.run_id,
            agent_name=self.name,
        )
        steps = run_data.get("steps", [])
        visited_urls = []
        for step in steps:
            observation = step.get("observation") or {}
            url = observation.get("url")
            if url:
                visited_urls.append(url)
                await context.shared_memory.record_route(url)
        confidence = min(0.95, 0.35 + len({url.split('#')[0] for url in visited_urls}) * 0.08)
        if run_data.get("status") == "completed":
            confidence = max(confidence, 0.7)
        findings = [
            MultiAgentFinding(
                agent_name=self.name,
                category="navigation_graph",
                severity="low",
                message=f"Discovered {len(set(visited_urls))} navigation states.",
                root_cause="navigation expansion",
                url=visited_urls[-1] if visited_urls else str(context.request.url),
                confidence=confidence,
                evidence={"visited_urls": visited_urls[:20]},
            )
        ]
        return AgentExecutionResult(
            agent_name=self.name,
            status=str(run_data.get("status") or "completed"),
            confidence=confidence,
            summary=f"Visited {len(set(visited_urls))} navigation states.",
            findings=findings,
            run=run_data,
        )
