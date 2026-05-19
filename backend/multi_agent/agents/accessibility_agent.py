from __future__ import annotations

from typing import Any, Dict, Optional

from backend.accessibility.service import AccessibilityAuditService
from backend.agent.browser_session import BrowserSession
from backend.agent.observer import BrowserObserver
from backend.agent.services.page_classifier import PageClassifier
from backend.multi_agent.base_agent import AgentRuntimeContext, BaseMultiAgent
from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding


class AccessibilityAgent(BaseMultiAgent):
    name = "AccessibilityAgent"
    confidence_floor = 0.45

    def __init__(self) -> None:
        super().__init__()
        self.observer = BrowserObserver()
        self.classifier = PageClassifier()
        self.audit_service = AccessibilityAuditService()

    async def execute(self, context: AgentRuntimeContext, session: Optional[BrowserSession], plan: Dict[str, Any]) -> AgentExecutionResult:
        if session is None:
            raise RuntimeError("AccessibilityAgent requires a browser session")
        observation = await self.observer.observe(session.page, context.run_id, 0, session.signals.console_errors, session.signals.network_failures, session.signals.dialogs, session.signals.popups)
        page_classification = self.classifier.classify(observation)
        audit = self.audit_service.audit(observation)
        findings = []
        for item in audit.get("findings", []):
            finding = MultiAgentFinding(
                agent_name=self.name,
                category=str(item.get("type", "accessibility")),
                severity=str(item.get("severity", "medium")),
                message=str(item.get("description", "Accessibility finding detected.")),
                root_cause=str(item.get("type", "accessibility_issue")),
                url=observation.url,
                workflow_state=page_classification.page_type,
                confidence=0.75 if item.get("severity") == "high" else 0.6,
                evidence={"element_index": item.get("element_index")},
            )
            findings.append(finding)
            await context.shared_memory.record_bug(finding)
        await context.coverage.record_accessibility(len(findings))
        await context.shared_memory.record_screenshot(
            agent_name=self.name,
            path=observation.screenshot.path if observation.screenshot else "",
            url=observation.url,
            workflow_state=page_classification.page_type,
        )
        confidence = min(0.99, float(audit.get("accessibility_score", 0)) / 100.0)
        status = "completed" if not findings else "completed_with_findings"
        return AgentExecutionResult(
            agent_name=self.name,
            status=status,
            confidence=confidence,
            summary=f"Accessibility score {audit.get('accessibility_score', 0)}.",
            findings=findings or [MultiAgentFinding(
                agent_name=self.name,
                category="accessibility",
                severity="low",
                message="No accessibility blockers detected by heuristic audit.",
                root_cause="accessibility audit clean",
                url=observation.url,
                workflow_state=page_classification.page_type,
                confidence=confidence,
            )],
            run={"observation": observation.model_dump(mode="json"), "audit": audit},
        )
