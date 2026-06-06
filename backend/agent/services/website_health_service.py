import asyncio
import logging
from typing import Any, Dict, List

from .success_detector import SuccessDetector
from .network_analysis_service import NetworkAnalysisService
from .visual_issue_service import VisualIssueService
from .bug_detection_service import BugDetectionService

logger = logging.getLogger(__name__)


class WebsiteHealthService:
    """Aggregates detectors and produces a website health summary.

    Expected input: execution_artifacts dict with keys produced by the executor:
      - dom_snapshot (str / json)
      - console_logs (List[dict])
      - network_logs (List[dict])
      - screenshots (List[path])
      - metadata (dict)
    """

    def __init__(self) -> None:
        self.success = SuccessDetector()
        self.network = NetworkAnalysisService()
        self.visual = VisualIssueService()
        self.bug = BugDetectionService()

    async def analyze(self, execution_artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Run all analyses in parallel and return consolidated health report."""
        logger.info("Starting website health analysis for execution %s", execution_artifacts.get("execution_id"))

        tasks = [
            asyncio.create_task(self.success.detect_all(execution_artifacts)),
            asyncio.create_task(self.network.analyze_network(execution_artifacts.get("network_logs", []))),
            asyncio.create_task(self.visual.analyze_visuals(execution_artifacts.get("screenshots", []))),
            asyncio.create_task(self.bug.find_bugs(execution_artifacts)),
        ]

        done = await asyncio.gather(*tasks)

        success_report, network_report, visual_report, bug_report = done

        # Simple scoring heuristic
        score = 100
        score -= min(50, len(network_report.get("errors", [])) * 6)
        score -= min(30, len(visual_report.get("issues", [])) * 4)
        score -= min(40, len(bug_report.get("issues", [])) * 8)
        score -= 0 if success_report.get("all_ok", False) else 20

        health = {
            "website_health_score": max(0, int(score)),
            "success_report": success_report,
            "network_report": network_report,
            "visual_report": visual_report,
            "bug_report": bug_report,
        }

        logger.info("Website health analysis complete: score=%s", health["website_health_score"])
        return health
