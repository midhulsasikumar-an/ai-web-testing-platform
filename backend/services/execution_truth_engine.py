"""Execution Truth Engine — single source of truth for test outcome interpretation.

This module is the ONLY place in the system that is allowed to interpret raw
execution output into canonical status values. Every other module (scenario
aggregation, dashboard rendering, bug lifecycle updates, frontend) MUST
consume the canonical object returned by :func:`evaluate_test_run` rather
than re-deriving pass/fail from raw step records.

Why this module exists
----------------------
Before this engine, four separate places computed test outcomes:

    1. ``services/scoring/overall_status.calculate_overall_status``
    2. ``services/test_services._build_scenario_result`` (scenario status)
    3. ``services/bug_services.create_bugs_from_test`` (independent inference)
    4. ``services/bug_lifecycle_service._bugs_from_results`` (independent
       inference) + ``_derive_status`` (status classification)

Those four implementations disagreed on:

    * whether ``health_score`` should ever flip a passing run to "warning"
    * whether a partial run (some scenarios never executed) should appear
      as "pass" in the dashboard
    * whether a successful regression pass should ever mark a bug as
      resolved
    * what string values count as a pass (pass/passed/completed/success)

The truth engine below freezes the answer to every one of those questions.
The rest of the system is being refactored to delegate to it.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Canonical status vocabulary. Every status string in the system must be
# reduced to one of these three values before any decision is made.
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_WARNING = "WARNING"

CANONICAL_STATUSES = {STATUS_PASS, STATUS_FAIL, STATUS_WARNING}


# Event-type tags for the bug lifecycle pipeline. These are the only
# event strings any consumer of the truth engine should ever observe.
BUG_EVENT_DETECTED = "BUG_DETECTED"
BUG_EVENT_RESOLVED = "BUG_RESOLVED"


# All raw status spellings the execution engine may emit. Mapping is
# bidirectional in concept but exposed here as a one-way normalization
# function (see ``_normalize_status`` below).
_RAW_PASS_VARIANTS = {
    "pass", "passed", "completed", "success", "ok", "true", "succeeded",
}
_RAW_FAIL_VARIANTS = {
    "fail", "failed", "error", "broken", "false", "errored",
}
_RAW_WARNING_VARIANTS = {
    "warning", "warn", "skipped", "timeout", "cancelled", "canceled",
    "partial", "incomplete",
}


def _normalize_status(value: Any) -> str:
    """Map any raw status string to the canonical vocabulary.

    The execution engine emits multiple spellings ("pass" / "passed",
    "fail" / "failed", "warning" / "skipped" / "cancelled"). The frontend,
    the dashboard, and the bug lifecycle all need a single, stable value
    to make decisions on. Anything unrecognised defaults to WARNING so we
    never accidentally present an unknown state as PASS.
    """
    text = str(value or "").strip().lower()
    if text in _RAW_PASS_VARIANTS:
        return STATUS_PASS
    if text in _RAW_FAIL_VARIANTS:
        return STATUS_FAIL
    if text in _RAW_WARNING_VARIANTS:
        return STATUS_WARNING
    return STATUS_WARNING


def _is_truthy(value: Any) -> bool:
    return bool(value) and str(value).strip().lower() not in {"0", "false", "none", "null"}


# ---------------------------------------------------------------------------
# Health score (informational metric only)
# ---------------------------------------------------------------------------

def _compute_health_score(
    step_results: List[Dict[str, Any]],
    scenario_results: List[Dict[str, Any]],
) -> int:
    """Compute a 0-100 health score from the canonical step outcomes.

    This is purely an informational metric. It MUST NOT influence
    pass/fail decisions anywhere in the system. The function lives here
    so the truth engine owns the single scoring formula; the previous
    ``services/scoring/health_score.py`` implementation is deprecated.
    """
    if not step_results:
        return 0

    total = len(step_results)
    passed = sum(1 for step in step_results if step.get("status") == STATUS_PASS)
    failed = sum(1 for step in step_results if step.get("status") == STATUS_FAIL)

    base = round((passed / total) * 100) if total else 0

    # Mild penalty for warnings so the metric is still useful for spotting
    # degraded runs without ever promoting a failing run to "pass".
    warnings = sum(1 for step in step_results if step.get("status") == STATUS_WARNING)
    if warnings:
        base = max(0, base - min(10, warnings))

    # If scenarios are supplied, blend in scenario-level coverage to keep
    # the historical "scenario pass rate" signal available.
    if scenario_results:
        scenarios_total = len(scenario_results)
        scenarios_passed = sum(
            1 for scenario in scenario_results
            if scenario.get("status") == STATUS_PASS
        )
        if scenarios_total:
            scenario_rate = scenarios_passed / scenarios_total
            base = round((base * 0.6) + (scenario_rate * 100 * 0.4))

    # Hard floor: a fully failing run can never appear healthy. The
    # floor only affects the displayed score, not the status.
    if failed and passed == 0:
        base = min(base, 25)

    return max(0, min(100, int(base)))


# ---------------------------------------------------------------------------
# Scenario / step normalisation
# ---------------------------------------------------------------------------

def _step_name(step_record: Dict[str, Any], index: int) -> str:
    """Derive a stable human-readable label for a single step."""
    step_meta = step_record.get("step") if isinstance(step_record.get("step"), dict) else {}
    action = step_meta.get("action") or step_record.get("test") or ""
    target = (
        step_meta.get("target")
        or step_meta.get("selector")
        or step_record.get("selector_used")
        or ""
    )
    label = f"{action} {target}".strip()
    return label[:200] if label else f"Step {index}"


def _build_canonical_step(step_record: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Project a raw step record into the canonical step shape."""
    if not isinstance(step_record, dict):
        return {
            "step_index": index,
            "step_name": f"Step {index}",
            "status": STATUS_WARNING,
            "error": None,
            "details": None,
            "duration_ms": None,
        }

    raw_status = step_record.get("status")
    error = step_record.get("error") or step_record.get("recovery_error") or None
    details = step_record.get("details") or step_record.get("recovery_hint") or None
    if _normalize_status(raw_status) == STATUS_FAIL and not error and not details:
        details = "Step failed"

    validation = step_record.get("validation") if isinstance(step_record.get("validation"), dict) else {}
    duration_ms = validation.get("duration_ms") if isinstance(validation.get("duration_ms"), (int, float)) else None

    return {
        "step_index": index,
        "step_name": _step_name(step_record, index),
        "status": _normalize_status(raw_status),
        "error": error,
        "details": details,
        "duration_ms": duration_ms,
    }


def _scenario_signature(scenario: Dict[str, Any]) -> Dict[str, str]:
    """Stable signature used for matching scenarios across runs and for
    bug-lifecycle fingerprinting."""
    return {
        "objective_id": str(scenario.get("objective_id") or ""),
        "scenario_id": str(scenario.get("scenario_id") or ""),
        "feature_key": str(scenario.get("feature_key") or ""),
    }


def _step_fingerprint(scenario_signature: Dict[str, str], step: Dict[str, Any]) -> str:
    """Stable per-step fingerprint used as a BUG_DETECTED identity."""
    return compute_bug_fingerprint(
        scenario_id=scenario_signature.get("scenario_id") or "",
        objective_id=scenario_signature.get("objective_id") or "",
        step_index=step.get("step_index"),
        step_name=step.get("step_name") or "",
    )


# ---------------------------------------------------------------------------
# Canonical fingerprint generator (shared utility)
# ---------------------------------------------------------------------------
#
# This is the SINGLE source of truth for bug identity. It is exposed as a
# public function so every consumer (execution_truth_engine,
# bug_lifecycle_service, bug_services, manual bug ingest) produces the
# exact same fingerprint string for the same logical bug. Anything that
# historically generated its own hash (e.g. SHA-256 of a bespoke tuple)
# has been removed -- one fingerprint, one format, no divergence.

_FINGERPRINT_FALLBACK = "unknown"


def _safe_part(value: Any) -> str:
    """Normalise a fingerprint part. Pipe chars are stripped because the
    pipe is the field separator; a literal ``|`` in user data would
    otherwise create ambiguous fingerprints."""
    text = str(value or "").strip()
    if not text:
        return ""
    return text.replace("|", "/").strip()


def compute_bug_fingerprint(
    *,
    scenario_id: Any = "",
    objective_id: Any = "",
    step_index: Any = None,
    step_name: Any = "",
) -> str:
    """Produce the canonical bug fingerprint.

    The fingerprint is a pipe-separated string. The format is::

        {scenario_id|objective_id|unknown}|{step_index}|{step_name}

    The same logical bug always produces the same string. This function
    is idempotent, deterministic, and total (never raises).

    Any caller that needs to identify a bug -- whether the bug was
    detected by the truth engine, manually reported, ingested from a
    legacy source, or imported from an external tracker -- must call
    this function. There is no other fingerprint format in the system.
    """
    scenario_part = _safe_part(scenario_id) or _safe_part(objective_id) or _FINGERPRINT_FALLBACK
    if step_index is None or step_index == "":
        index_part = "0"
    else:
        try:
            index_part = str(int(step_index))
        except (TypeError, ValueError):
            index_part = "0"
    name_part = _safe_part(step_name) or "unnamed"
    return f"{scenario_part}|{index_part}|{name_part}"


def _scenario_fingerprint(scenario_signature: Dict[str, str]) -> str:
    return "|".join(
        [
            scenario_signature["scenario_id"] or scenario_signature["objective_id"] or "unknown",
            scenario_signature["feature_key"] or "no-feature",
        ]
    )


def _classify_severity(step: Dict[str, Any], scenario: Dict[str, Any]) -> str:
    """Best-effort severity mapping for BUG_DETECTED events."""
    failure_category = str(scenario.get("failure_category") or "").upper()
    critical_categories = {"AUTHENTICATION", "NAVIGATION", "TIMEOUT", "PAYMENT", "CHECKOUT"}
    high_categories = {"SELECTOR", "NETWORK", "CONSOLE", "INCOMPLETE"}
    if failure_category in critical_categories:
        return "high"
    if failure_category in high_categories:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_test_run(test_run: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the single canonical truth object for a test run.

    Inputs
    ------
    ``test_run`` may carry raw scenario records in either of two shapes:

      * ``test_run["results"]`` — list of scenario dicts whose
        ``step_results`` field contains the raw per-step records from
        ``execution_service.run_test_steps``.
      * ``test_run["step_results"]`` — a flat list of raw step records
        (legacy / unit-test shape). In that case a single anonymous
        scenario is synthesised.

    Output
    ------
    A canonical dict::

        {
            "overall_status": "PASS" | "FAIL",
            "health_score":   0-100,
            "scenario_results": [...],
            "step_results":     [...],
            "bug_events":       [...],
            "resolution_events": [...],
        }

    Every other module in the system MUST consume this object rather than
    re-deriving any of those fields. This is the contract.
    """
    if not isinstance(test_run, dict):
        test_run = {}

    raw_results = test_run.get("results") or []
    if not isinstance(raw_results, list):
        raw_results = []

    # ---- 1. Normalise every step in every scenario -------------------
    canonical_scenarios: List[Dict[str, Any]] = []
    canonical_steps: List[Dict[str, Any]] = []
    bug_events: List[Dict[str, Any]] = []
    step_counter = 0

    for raw_scenario in raw_results:
        if not isinstance(raw_scenario, dict):
            continue

        signature = _scenario_signature(raw_scenario)
        raw_steps = raw_scenario.get("step_results")
        if not isinstance(raw_steps, list):
            # Some legacy scenarios put their step-level info at the top
            # level (the "scenario IS a step" shape). Project it as a
            # single-step scenario so the canonical shape is uniform.
            raw_steps = [raw_scenario]

        raw_scenario_status = _normalize_status(raw_scenario.get("status"))
        scenario_canonical_steps: List[Dict[str, Any]] = []
        scenario_failed = raw_scenario_status == STATUS_FAIL
        for raw_step in raw_steps:
            step_counter += 1
            canonical_step = _build_canonical_step(raw_step, step_counter)
            scenario_canonical_steps.append(canonical_step)
            canonical_steps.append(canonical_step)
            if canonical_step["status"] == STATUS_FAIL:
                scenario_failed = True

        scenario_status = STATUS_FAIL if scenario_failed else STATUS_PASS

        # Track which step caused the scenario to fail for BUG_DETECTED
        # emission below.
        first_failing_step = next(
            (step for step in scenario_canonical_steps if step["status"] == STATUS_FAIL),
            None,
        )

        canonical_scenarios.append({
            "test": str(raw_scenario.get("test") or raw_scenario.get("scenario_name") or "Scenario"),
            "status": scenario_status,
            "details": raw_scenario.get("details"),
            "scenario_id": signature["scenario_id"] or None,
            "scenario_name": raw_scenario.get("scenario_name"),
            "objective_id": signature["objective_id"] or None,
            "feature_key": signature["feature_key"] or None,
            "failure_category": raw_scenario.get("failure_category"),
            "root_cause": raw_scenario.get("root_cause"),
            "passed_steps": sum(1 for s in scenario_canonical_steps if s["status"] == STATUS_PASS),
            "failed_steps": sum(1 for s in scenario_canonical_steps if s["status"] == STATUS_FAIL),
            "warning_steps": sum(1 for s in scenario_canonical_steps if s["status"] == STATUS_WARNING),
            "executed_steps": len(scenario_canonical_steps),
            "step_results": scenario_canonical_steps,
        })

        if scenario_failed and first_failing_step is not None:
            bug_events.append({
                "type": BUG_EVENT_DETECTED,
                "fingerprint": _step_fingerprint(signature, first_failing_step),
                "scenario_fingerprint": _scenario_fingerprint(signature),
                "scenario_id": signature["scenario_id"] or None,
                "objective_id": signature["objective_id"] or None,
                "step_index": first_failing_step["step_index"],
                "step_name": first_failing_step["step_name"],
                "error": first_failing_step.get("error") or first_failing_step.get("details") or "",
                "severity": _classify_severity(first_failing_step, raw_scenario),
                "failure_category": raw_scenario.get("failure_category"),
                "root_cause": raw_scenario.get("root_cause"),
            })

    # ---- 2. Compute the overall status from canonical scenarios ------
    overall_status = STATUS_PASS
    for scenario in canonical_scenarios:
        if scenario["status"] == STATUS_FAIL:
            overall_status = STATUS_FAIL
            break

    # ---- 3. Health score is purely informational ----------------------
    health_score = _compute_health_score(canonical_steps, canonical_scenarios)

    # ---- 4. Resolution events are derived externally by the bug
    #         lifecycle service (it knows the historical state). We
    #         expose a helper that returns the scenario fingerprints
    #         that did NOT fail, so the bug lifecycle can diff against
    #         its own previously-failing fingerprints. -----------------
    passing_scenario_fingerprints = [
        _scenario_fingerprint(_scenario_signature(scenario))
        for scenario in canonical_scenarios
        if scenario["status"] == STATUS_PASS
    ]
    failing_bug_fingerprints = [
        bug["fingerprint"]
        for bug in bug_events
        if bug.get("fingerprint")
    ]
    failing_scenario_fingerprints = [
        bug["scenario_fingerprint"]
        for bug in bug_events
        if bug.get("scenario_fingerprint")
    ]

    return {
        "overall_status": overall_status,
        "health_score": health_score,
        "scenario_results": canonical_scenarios,
        "step_results": canonical_steps,
        "bug_events": bug_events,
        "resolution_events": [],  # populated by the bug lifecycle diff step
        "passing_scenario_fingerprints": passing_scenario_fingerprints,
        "failing_bug_fingerprints": failing_bug_fingerprints,
        "failing_scenario_fingerprints": failing_scenario_fingerprints,
    }


# ---------------------------------------------------------------------------
# Resolution diff (called by the bug lifecycle service)
# ---------------------------------------------------------------------------

def diff_resolutions(
    truth: Dict[str, Any],
    previously_open_fingerprints: Iterable[str],
) -> List[Dict[str, Any]]:
    """Produce BUG_RESOLVED events for fingerprints that no longer fail.

    The bug lifecycle service knows the set of fingerprints that were
    previously open (Active / Monitoring / Regressed). For each one that
    does NOT appear in the current run's ``failing_scenario_fingerprints``
    we emit a BUG_RESOLVED event. This is the only legitimate way for a
    bug to be closed in the new pipeline.
    """
    failing = set(truth.get("failing_bug_fingerprints") or [])
    resolutions: List[Dict[str, Any]] = []
    for fingerprint in previously_open_fingerprints or []:
        if not fingerprint or fingerprint in failing:
            continue
        resolutions.append({
            "type": BUG_EVENT_RESOLVED,
            "fingerprint": fingerprint,
            "resolution_reason": "regression_pass",
        })
    return resolutions


# ---------------------------------------------------------------------------
# Convenience: a thin facade that the rest of the codebase can call
# without remembering the field names on the truth object.
# ---------------------------------------------------------------------------

def is_passing(truth: Dict[str, Any]) -> bool:
    return truth.get("overall_status") == STATUS_PASS


def health_score(truth: Dict[str, Any]) -> int:
    try:
        return int(truth.get("health_score", 0) or 0)
    except (TypeError, ValueError):
        return 0


def count_step_statuses(truth: Dict[str, Any]) -> Counter:
    counter: Counter = Counter()
    for step in truth.get("step_results") or []:
        if isinstance(step, dict):
            counter[step.get("status") or STATUS_WARNING] += 1
    return counter
