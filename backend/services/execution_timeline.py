from __future__ import annotations

from typing import Any, Dict, List


def _event_label(entry: Dict[str, Any]) -> str:
    event_type = str(entry.get("type") or "").strip().lower()
    if event_type == "terminal_summary":
        return "Run finalized"
    if event_type == "target_blocked":
        return "Target blocked"
    if event_type == "run_status":
        return "Run status"
    if event_type == "action_translation":
        return "Action translated"
    if event_type == "screenshot":
        return "Screenshot captured"
    if event_type == "bug_detected":
        return "Bug detected"
    if event_type == "scenario_dependency_skip":
        return "Scenario skipped"
    return event_type.replace("_", " ").title() if event_type else "Execution event"


def build_execution_timeline(run: Dict[str, Any], *, limit: int = 120) -> List[Dict[str, Any]]:
    logs = run.get("stream_logs") if isinstance(run.get("stream_logs"), list) else []
    timeline: List[Dict[str, Any]] = []
    for index, entry in enumerate(logs[-limit:]):
        if not isinstance(entry, dict):
            continue
        details = entry.get("details") if isinstance(entry.get("details"), dict) else {}
        level = str(entry.get("level") or "info").lower()
        timeline.append({
            "id": f"{run.get('test_id') or run.get('execution_id') or 'run'}-{index}",
            "time": entry.get("time") or run.get("updated_at") or run.get("created_at"),
            "phase": entry.get("type") or "event",
            "label": _event_label(entry),
            "message": entry.get("msg") or details.get("message") or "",
            "level": level,
            "scenario_id": details.get("scenario_id"),
            "scenario_name": details.get("scenario_name"),
            "step_index": details.get("step_index"),
            "duration_seconds": details.get("duration_seconds"),
            "screenshot": details.get("screenshot"),
        })
    return timeline


def build_blocked_diagnostics(run: Dict[str, Any]) -> Dict[str, Any] | None:
    failure_type = str(run.get("failure_type") or "").lower()
    if failure_type != "target_blocked":
        return None
    return {
        "title": "Target blocked automation",
        "reason": run.get("failure_reason") or "security_checkpoint",
        "message": "The target served a security or owner checkpoint instead of the requested app page.",
        "is_testpulse_bug": False,
        "recommended_actions": [
            "Run against a staging or preview URL without bot protection.",
            "Allowlist the Render backend or test user agent if you own the target site.",
            "Open the target manually and confirm the requested page is reachable before re-running.",
        ],
    }
