"""Deprecated shim — delegates to the centralised truth engine.

This module used to independently compute pass/fail from raw results and
silently flipped passing runs to "warning" whenever ``health_score < 85``.
That double-source-of-truth was the root cause of the dashboard-vs-data
discrepancy. It has been removed.

Kept as a thin shim so legacy callers (``test_services.py`` and the
``scoring`` package) still work, but every code path now routes through
:mod:`backend.services.execution_truth_engine`. New code MUST call
``evaluate_test_run`` directly.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from backend.services.execution_truth_engine import (
    STATUS_FAIL,
    STATUS_PASS,
    evaluate_test_run,
)


def calculate_overall_status(
    results: Optional[Iterable[Dict[str, Any]]],
    insights: Any = None,
    health_score: Any = None,
) -> str:
    """Backwards-compatible wrapper around :func:`evaluate_test_run`.

    Returns one of ``"pass"`` or ``"fail"`` (lowercase to match the
    historical API contract; the truth engine itself uses the canonical
    uppercase vocabulary). The ``insights`` and ``health_score``
    parameters are accepted but ignored: per the new system contract,
    health score MUST NOT influence pass/fail.
    """
    del insights, health_score  # signature kept for backwards compatibility
    truth = evaluate_test_run({"results": list(results or [])})
    canonical = truth.get("overall_status")
    if canonical == STATUS_FAIL:
        return "fail"
    if canonical == STATUS_PASS:
        return "pass"
    # Truth engine never returns anything but PASS/FAIL today, but in
    # case a future canonical value is added we degrade safely to "fail"
    # so the dashboard never silently misreports a non-passing state.
    return "fail"
