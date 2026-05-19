from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.browser_session import BrowserSession
from backend.agent.observer import BrowserObserver
from backend.agent.services.page_classifier import PageClassifier
from backend.agent.vision.visual_diff import VisualDiff
from backend.multi_agent.base_agent import AgentRuntimeContext, BaseMultiAgent
from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding


class VisualQAAgent(BaseMultiAgent):
    name = "VisualQAAgent"
    confidence_floor = 0.45

    def __init__(self) -> None:
        super().__init__()
        self.observer = BrowserObserver()
        self.classifier = PageClassifier()
        self.visual_diff = VisualDiff()

    async def execute(self, context: AgentRuntimeContext, session: Optional[BrowserSession], plan: Dict[str, Any]) -> AgentExecutionResult:
        if session is None:
            raise RuntimeError("VisualQAAgent requires a browser session")
        observation = await self.observer.observe(session.page, context.run_id, 0, session.signals.console_errors, session.signals.network_failures, session.signals.dialogs, session.signals.popups)
        page_classification = self.classifier.classify(observation)
        previous = (await context.shared_memory.snapshot()).get("screenshots", [])
        findings = []
        confidence = 0.65
        if previous:
            previous_screenshot = previous[-1].get("path")
            current_screenshot = observation.screenshot.path if observation.screenshot else None
            if previous_screenshot and current_screenshot:
                diff = self.visual_diff.compare_screenshots(previous_screenshot, current_screenshot)
                confidence = max(0.5, 1.0 - diff.change_score)
                if diff.significant_change:
                    finding = MultiAgentFinding(
                        agent_name=self.name,
                        category="visual_regression",
                        severity="medium" if diff.change_score < 0.5 else "high",
                        message=diff.change_description,
                        root_cause="visual regression",
                        url=observation.url,
                        workflow_state=page_classification.page_type,
                        confidence=confidence,
                        evidence=diff.to_dict(),
                    )
                    findings.append(finding)
                    await context.shared_memory.record_bug(finding)
        if observation.screenshot:
            await context.shared_memory.record_screenshot(
                agent_name=self.name,
                path=observation.screenshot.path,
                url=observation.url,
                workflow_state=page_classification.page_type,
            )
        return AgentExecutionResult(
            agent_name=self.name,
            status="completed" if not findings else "completed_with_findings",
            confidence=confidence,
            summary="Visual QA completed.",
            findings=findings or [MultiAgentFinding(
                agent_name=self.name,
                category="visual_qa",
                severity="low",
                message="Visual baseline captured without a significant regression.",
                root_cause="visual baseline",
                url=observation.url,
                workflow_state=page_classification.page_type,
                confidence=confidence,
                evidence={"screenshot": observation.screenshot.path if observation.screenshot else None},
            )],
            run={"observation": observation.model_dump(mode="json")},
        )
