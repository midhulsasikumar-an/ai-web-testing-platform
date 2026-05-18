import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BugDetectionService:
    """Generate QA findings from combined execution artifacts.

    This service receives the execution_artifacts and optional detector outputs
    and returns a list of issues with severity and evidence.
    """

    async def find_bugs(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        # Collect console errors
        console = artifacts.get("console_logs") or []
        for c in console:
            if c.get("level") in ("error", "uncaught") or c.get("type") == "error":
                issues.append(self._make_issue("critical", 0.95, "console_error", c))

        # Network failures (if provided)
        network = artifacts.get("network_logs") or []
        for n in network:
            st = n.get("status")
            if isinstance(st, int) and 500 <= st < 600:
                issues.append(self._make_issue("high", 0.9, "server_error", n))
            if st == 0 or n.get("error"):
                issues.append(self._make_issue("medium", 0.7, "network_failure", n))

        # Visual issues
        visual = artifacts.get("visual_report") or {}
        for v in visual.get("issues", []):
            sev = "low"
            conf = 0.5
            if v.get("issue") in ("blank_or_near_blank", "extreme_aspect_ratio"):
                sev = "high"
                conf = 0.85
            issues.append(self._make_issue(sev, conf, "visual", v))

        # Success detector
        success = artifacts.get("success_report") or {}
        if not success.get("all_ok", True):
            issues.append(self._make_issue("critical", 0.9, "workflow_failure", {"details": success.get("checks")}))

        return {"issues": issues}

    def _make_issue(self, severity: str, confidence: float, category: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        impact_map = {
            "critical": "Users can not use core functionality",
            "high": "High impact on feature stability",
            "medium": "Partial feature degradation",
            "low": "Visual or minor UX issue",
        }
        return {
            "severity": severity,
            "confidence": float(confidence),
            "category": category,
            "impact": impact_map.get(severity, "Unknown"),
            "reproduction_steps": [],
            "evidence": evidence,
        }
