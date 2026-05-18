from __future__ import annotations

from typing import Any, Dict, List


def analyze_performance(steps: List[Dict[str, Any]], run_summary: Dict[str, Any] | None = None) -> Dict[str, Any]:
    run_summary = run_summary or {}
    slow_actions = []
    for idx, step in enumerate(steps):
        result = step.get("result") or {}
        duration = result.get("duration_ms") or 0
        observation = step.get("observation") or {}
        console_errors = observation.get("console_errors") or []
        if duration and duration >= 3000:
            slow_actions.append({
                "step": idx,
                "type": "slow_action",
                "duration_ms": duration,
                "workflow_stage": observation.get("page_type") or step.get("workflow_state_after") or "unknown",
                "impact": "Long action latency may indicate slow APIs or heavy rendering.",
            })
        if any(term in " ".join(console_errors).lower() for term in ["long task", "hydration", "layout shift", "memory"]):
            slow_actions.append({
                "step": idx,
                "type": "console_performance_warning",
                "duration_ms": duration,
                "workflow_stage": observation.get("page_type") or step.get("workflow_state_after") or "unknown",
                "impact": "Browser console reported a performance-related warning.",
            })
    score = max(0, 100 - len(slow_actions) * 10)
    return {
        "performance_score": score,
        "findings": slow_actions,
        "slow_api_risk": any(item["type"] == "slow_action" for item in slow_actions),
        "console_performance_risk": any(item["type"] == "console_performance_warning" for item in slow_actions),
        "memory_spike_risk": any("memory" in item.get("impact", "").lower() for item in slow_actions),
        "layout_shift_risk": any("layout" in item.get("impact", "").lower() for item in slow_actions),
    }
