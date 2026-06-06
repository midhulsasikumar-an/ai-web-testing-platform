from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.agent_loop_v2 import run_agent_loop_v2
from backend.agent.browser_session import BrowserSession
from backend.multi_agent.base_agent import AgentRuntimeContext, BaseMultiAgent
from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding


class AuthenticationAgent(BaseMultiAgent):
    name = "AuthenticationAgent"
    confidence_floor = 0.65

    async def execute(self, context: AgentRuntimeContext, session: Optional[BrowserSession], plan: Dict[str, Any]) -> AgentExecutionResult:
        if session is None:
            raise RuntimeError("AuthenticationAgent requires a browser session")
        run_data = await run_agent_loop_v2(
            page=session.page,
            goal="authenticate_user",
            credentials=context.request.credentials,
            start_url=str(context.request.url),
            max_steps=context.request.max_steps,
            same_origin_only=True,
            signals=session.signals,
            event_bus=context.bus,
            run_id=context.run_id,
            agent_name=self.name,
        )
        summary = run_data.get("summary", {}) if isinstance(run_data.get("summary"), dict) else {}
        authenticated = bool(summary.get("authenticated") or summary.get("authentication_result") == "authenticated")
        confidence = float(summary.get("authentication_confidence") or (0.9 if authenticated else 0.55))
        findings = []
        if authenticated:
            findings.append(MultiAgentFinding(
                agent_name=self.name,
                category="authentication",
                severity="low",
                message="Authentication completed successfully.",
                root_cause="authentication flow succeeded",
                url=run_data.get("current_url") or str(context.request.url),
                confidence=confidence,
                evidence={"strategy": summary.get("authentication_strategy", "")},
            ))
        else:
            findings.append(MultiAgentFinding(
                agent_name=self.name,
                category="authentication",
                severity="high",
                message="Authentication did not reach an authenticated state.",
                root_cause=summary.get("authentication_result") or "authentication failure",
                url=run_data.get("current_url") or str(context.request.url),
                confidence=confidence,
                evidence={"reasoning": summary.get("authentication_reasoning", [])},
            ))
        await context.shared_memory.set_auth_session(
            authenticated=authenticated,
            confidence=confidence,
            details={"summary": summary, "run_status": run_data.get("status")},
        )
        return AgentExecutionResult(
            agent_name=self.name,
            status=str(run_data.get("status") or "completed"),
            confidence=confidence,
            summary=summary.get("authentication_result") or ("authenticated" if authenticated else "authentication incomplete"),
            findings=findings,
            run=run_data,
        )
