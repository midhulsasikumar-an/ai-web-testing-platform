from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.browser_session import BrowserSession
from backend.agent.observer import BrowserObserver
from backend.agent.services.page_classifier import PageClassifier
from backend.multi_agent.base_agent import AgentRuntimeContext, BaseMultiAgent
from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding
from backend.services.performance_analysis_service import analyze_performance


class PerformanceAgent(BaseMultiAgent):
    name = "PerformanceAgent"
    confidence_floor = 0.45

    def __init__(self) -> None:
        super().__init__()
        self.observer = BrowserObserver()
        self.classifier = PageClassifier()

    async def execute(self, context: AgentRuntimeContext, session: Optional[BrowserSession], plan: Dict[str, Any]) -> AgentExecutionResult:
        if session is None:
            raise RuntimeError("PerformanceAgent requires a browser session")
        observation = await self.observer.observe(session.page, context.run_id, 0, session.signals.console_errors, session.signals.network_failures, session.signals.dialogs, session.signals.popups)
        page_classification = self.classifier.classify(observation)
        performance_data = await session.page.evaluate(
            """
            () => {
              const nav = performance.getEntriesByType('navigation')[0] || null;
              const paint = performance.getEntriesByType('paint').map(item => ({name: item.name, startTime: item.startTime, duration: item.duration}));
              const resources = performance.getEntriesByType('resource').slice(-25).map(item => ({name: item.name, duration: item.duration, transferSize: item.transferSize || 0}));
              const longTasks = performance.getEntriesByType('longtask').map(item => ({name: item.name, startTime: item.startTime, duration: item.duration}));
              const layoutShifts = performance.getEntriesByType('layout-shift').map(item => ({value: item.value, startTime: item.startTime, hadRecentInput: item.hadRecentInput}));
              return {navigation: nav ? {duration: nav.duration, domContentLoaded: nav.domContentLoadedEventEnd, loadEventEnd: nav.loadEventEnd, transferSize: nav.transferSize || 0} : null, paint, resources, longTasks, layoutShifts};
            }
            """
        )
        synthetic_steps = [
            {
                "observation": observation.model_dump(mode="json"),
                "result": {
                    "success": True,
                    "duration_ms": int(performance_data.get("navigation", {}).get("duration") or 0),
                    "error": None,
                },
            }
        ]
        analysis = analyze_performance(synthetic_steps, {"page_type": page_classification.page_type})
        findings = []
        for item in analysis.get("findings", []):
            finding = MultiAgentFinding(
                agent_name=self.name,
                category=str(item.get("type", "performance")),
                severity="medium",
                message=str(item.get("impact", "Performance issue detected.")),
                root_cause=item.get("type", "performance_issue"),
                url=observation.url,
                workflow_state=page_classification.page_type,
                confidence=0.7,
                evidence=item,
            )
            findings.append(finding)
            await context.shared_memory.record_bug(finding)
            await context.shared_memory.record_api_failure({"agent": self.name, "details": item})
        await context.coverage.record_performance(len(findings))
        confidence = min(0.99, float(analysis.get("performance_score", 0)) / 100.0)
        return AgentExecutionResult(
            agent_name=self.name,
            status="completed" if not findings else "completed_with_findings",
            confidence=confidence,
            summary=f"Performance score {analysis.get('performance_score', 0)}.",
            findings=findings or [MultiAgentFinding(
                agent_name=self.name,
                category="performance",
                severity="low",
                message="No obvious performance issues detected by heuristic analysis.",
                root_cause="performance audit clean",
                url=observation.url,
                workflow_state=page_classification.page_type,
                confidence=confidence,
            )],
            run={"observation": observation.model_dump(mode="json"), "performance": performance_data, "analysis": analysis},
        )
