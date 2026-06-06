from typing import Any, Dict

class GoalCompletionService:
    """Evaluate overall workflow goal progress and return granular states.

    Returns one of: completed, partially_completed, failed, blocked, unstable
    with a confidence score and details per goal.
    """

    async def evaluate(self, execution_artifacts: Dict[str, Any]) -> Dict[str, Any]:
        success = execution_artifacts.get("success_report") or {}
        bug_report = execution_artifacts.get("bug_report") or {}

        if success.get("all_ok", False) and not (bug_report.get("issues")):
            return {"state": "completed", "confidence": 0.98, "details": {}}

        issues = bug_report.get("issues", [])
        if issues:
            # if any critical issue present -> failed
            critical = [i for i in issues if i.get("severity") in ("critical", "high")]
            if critical:
                return {"state": "failed", "confidence": 0.9, "details": {"issues": critical}}
            return {"state": "partially_completed", "confidence": 0.75, "details": {"issues": issues}}

        # fallback
        return {"state": "unstable", "confidence": 0.5, "details": {"success_checks": success.get("checks")}}
