from __future__ import annotations

from typing import Any, Dict


RUNNING_STATUSES = {"queued", "planning", "running", "cancel_requested"}
TERMINAL_STATUSES = {"completed", "completed_with_failures", "failed", "timed_out", "timeout", "cancelled"}

TARGET_BLOCKED_MARKERS = {
    "vercel security checkpoint",
    "website owner? click here to fix",
    "security checkpoint",
    "bot protection",
    "cloudflare",
    "checking if the site connection is secure",
    "challenge",
}

BROWSER_ERROR_MARKERS = {
    "browsertype.launch",
    "executable doesn't exist",
    "chromium_headless_shell",
    "chrome-headless-shell",
    "playwright install",
    "browser executable",
}


def flatten_text(value: Any, *, limit: int = 20000) -> str:
    parts: list[str] = []

    def visit(item: Any) -> None:
        if len(" ".join(parts)) >= limit:
            return
        if item is None:
            return
        if isinstance(item, str):
            if item:
                parts.append(item)
            return
        if isinstance(item, (int, float, bool)):
            parts.append(str(item))
            return
        if isinstance(item, dict):
            for nested in item.values():
                visit(nested)
            return
        if isinstance(item, (list, tuple, set)):
            for nested in item:
                visit(nested)

    visit(value)
    return " ".join(parts).lower()[:limit]


def is_target_blocked(value: Any) -> bool:
    text = flatten_text(value)
    return any(marker in text for marker in TARGET_BLOCKED_MARKERS)


def is_browser_error(value: Any) -> bool:
    text = flatten_text(value)
    return any(marker in text for marker in BROWSER_ERROR_MARKERS)


def derive_run_outcome(run: Dict[str, Any]) -> Dict[str, Any]:
    status = str(run.get("status") or "").strip().lower()
    overall_status = str(run.get("overall_status") or "").strip().lower()
    failure_reason = str(run.get("failure_reason") or "").strip().lower()
    evidence = {
        "status": status,
        "overall_status": overall_status,
        "failure_reason": failure_reason,
        "results": run.get("results"),
        "stream_logs": run.get("stream_logs"),
        "ai_plan": run.get("ai_plan"),
        "discovery": run.get("discovery"),
        "discovery_status": run.get("discovery_status"),
        "discovery_error": run.get("discovery_error"),
        "page_title": run.get("page_title"),
    }

    if status in RUNNING_STATUSES:
        execution_status = status
        test_verdict = "unknown"
        failure_type = "none"
    elif status in {"timed_out", "timeout"}:
        execution_status = "timed_out"
        test_verdict = "blocked"
        failure_type = "timeout"
    elif status == "cancelled":
        execution_status = "cancelled"
        test_verdict = "unknown"
        failure_type = "none"
    elif is_browser_error(evidence):
        execution_status = "failed"
        test_verdict = "blocked"
        failure_type = "browser_error"
    elif is_target_blocked(evidence):
        execution_status = "failed" if status == "failed" else (status or "completed")
        test_verdict = "blocked"
        failure_type = "target_blocked"
    elif status == "completed" and overall_status == "pass":
        execution_status = "completed"
        test_verdict = "pass"
        failure_type = "none"
    elif status in {"completed", "completed_with_failures"} and overall_status in {"fail", "warning"}:
        execution_status = "completed"
        test_verdict = "fail"
        failure_type = "app_bug"
    elif status == "completed_with_failures":
        execution_status = "completed"
        test_verdict = "fail"
        failure_type = "app_bug"
    elif status == "failed":
        execution_status = "failed"
        test_verdict = "blocked"
        failure_type = "execution_error"
    elif overall_status == "pass":
        execution_status = status or "completed"
        test_verdict = "pass"
        failure_type = "none"
    elif overall_status in {"fail", "warning"}:
        execution_status = status or "completed"
        test_verdict = "fail"
        failure_type = "app_bug"
    else:
        execution_status = status or "unknown"
        test_verdict = "unknown"
        failure_type = "none"

    labels = {
        "pass": "Passed",
        "fail": "Website issues found",
        "blocked": {
            "target_blocked": "Target blocked automation",
            "browser_error": "Browser runtime unavailable",
            "timeout": "Execution timed out",
            "execution_error": "Execution failed",
        }.get(failure_type, "Run blocked"),
        "unknown": "In progress" if execution_status in RUNNING_STATUSES else "Unknown",
    }
    outcome_label = labels.get(test_verdict, "Unknown")

    return {
        "execution_status": execution_status,
        "test_verdict": test_verdict,
        "failure_type": failure_type,
        "outcome_label": outcome_label,
        "is_terminal": execution_status in TERMINAL_STATUSES or test_verdict in {"pass", "fail", "blocked"},
    }


def apply_run_outcome(run: Dict[str, Any]) -> Dict[str, Any]:
    outcome = derive_run_outcome(run)
    run.update(outcome)
    return run
