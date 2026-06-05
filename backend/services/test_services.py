import copy
import logging
import uuid
import traceback
import os
import base64
import asyncio
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional
from backend.database.mongo import collection, db
from backend.database.report_repository import save_report
from backend.models.schema import TestRequest
from backend.services.test_runner import run_test
from backend.services.execution_service import run_test_steps
from backend.services.scoring.health_score import calculate_health_score
from backend.services.scoring.insights import generate_insights
from backend.services.scoring.recommendations import generate_recommendations
from backend.services.scoring.report_generator import generate_report
from backend.services.scoring.ai_summary import generate_summary_line
from backend.services.scoring.overall_status import calculate_overall_status
from backend.services.bug_services import create_bugs_from_test
from backend.services.bug_lifecycle_service import (
    reconcile_bugs_on_passing_run,
    sync_bugs_collection_to_lifecycle,
)
from backend.services.execution_truth_engine import (
    BUG_EVENT_DETECTED,
    BUG_EVENT_RESOLVED,
    evaluate_test_run,
    is_passing as _truth_is_passing,
    health_score as _truth_health_score,
)
from backend.services.asset_auth import build_artifact_url, build_screenshot_url
from backend.utils.url_utils import canonicalize_url as _canonicalize_url
from backend.ai.schema.test_plan_schema import TestCase
from backend.services.dom_service import extract_page_elements
from backend.services.action_translation_service import translate_test_case
from backend.services.failure_classifier import classify_failure_category, collect_failure_category_counts
from backend.services.root_cause_classifier import classify_root_cause

logger = logging.getLogger("services.test")

OVERALL_EXECUTION_TIMEOUT_SECONDS = int(os.getenv("AI_PLAN_OVERALL_TIMEOUT_SECONDS", "3600"))


def _derive_progress_msg(evt: Dict[str, Any]) -> str:
    """
    Derive a human-readable stream_log message from a progress event.

    Many progress events in execution_service.py emit a structured `details` payload
    but no top-level `message` field. Writing `""` for those would render as blank
    terminal rows. This function preserves any explicit `message` and otherwise
    composes a short summary from the event type and structured fields.
    """
    explicit = evt.get("message")
    if isinstance(explicit, str) and explicit.strip():
        return explicit

    evt_type = evt.get("type")

    if evt_type == "timing":
        label = evt.get("label") or "event"
        phase = evt.get("phase") or ""
        elapsed = evt.get("elapsed_ms")
        if isinstance(elapsed, (int, float)):
            return f"⏱ {label} {phase} ({elapsed}ms)".strip()
        if phase:
            return f"⏱ {label} {phase}".strip()
        return f"⏱ {label}"

    if evt_type == "screenshot":
        label = evt.get("label") or "screenshot"
        if evt.get("screenshot_error"):
            return f"📸 {label} (error: {evt['screenshot_error']})"
        if evt.get("screenshot") or evt.get("screenshot_b64"):
            return f"📸 {label} captured"
        return f"📸 {label}"

    if evt_type == "selector_diagnostics":
        original = evt.get("original_target") or evt.get("step", {}).get("target") or "?"
        resolved = evt.get("resolved_selector")
        source = evt.get("source") or "?"
        confidence = evt.get("confidence")
        if resolved:
            conf = f", conf={confidence}" if isinstance(confidence, (int, float)) else ""
            return f"🔍 {original} → {resolved} (source={source}{conf})"
        return f"🔍 {original} unresolved (source={source})"

    if evt_type:
        return f"[{evt_type}]"

    return ""


def _collect_recovery_summary(results: List[Dict[str, Any]]) -> Dict[str, int]:
    recoveries_attempted = 0
    recoveries_successful = 0
    steps_saved_by_recovery = 0

    for result in results or []:
        if not isinstance(result, dict):
            continue

        recovery_history = result.get("recovery_history") if isinstance(result.get("recovery_history"), list) else []
        recoveries_attempted += len(recovery_history)
        recoveries_successful += sum(1 for attempt in recovery_history if isinstance(attempt, dict) and attempt.get("status") == "passed")

        recovery_actions = result.get("recovery_actions") if isinstance(result.get("recovery_actions"), list) else []
        recoveries_attempted += len(recovery_actions)
        recoveries_successful += sum(1 for action in recovery_actions if isinstance(action, dict) and action.get("success"))

        step_results = result.get("step_results") if isinstance(result.get("step_results"), list) else []
        for step_result in step_results:
            if not isinstance(step_result, dict):
                continue
            step_recovery_actions = step_result.get("recovery_actions") if isinstance(step_result.get("recovery_actions"), list) else []
            recoveries_attempted += len(step_recovery_actions)
            recoveries_successful += sum(1 for action in step_recovery_actions if isinstance(action, dict) and action.get("success"))

        if result.get("recovery_success"):
            steps_saved_by_recovery += 1

    return {
        "recoveries_attempted": recoveries_attempted,
        "recoveries_successful": recoveries_successful,
        "recovery_attempts": recoveries_attempted,
        "successful_recoveries": recoveries_successful,
        "steps_saved_by_recovery": steps_saved_by_recovery,
    }


def _apply_truth_engine(test_data: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run the canonical truth engine and stamp its verdict onto test_data.

    This is the only function in this module that is allowed to compute
    ``overall_status`` and ``health_score`` for a run. Every other
    function in the system must consume the values it writes.

    The truth engine normalises step statuses, computes scenario
    statuses, rolls up the overall status, computes a health-score
    metric (informational only), and emits BUG_DETECTED / BUG_RESOLVED
    events. The test_data dict receives the canonical fields:

      * ``overall_status``         -- "pass" | "fail"
      * ``health_score``           -- 0-100 informational integer
      * ``scenario_results``       -- canonical per-scenario records
      * ``step_results``           -- canonical per-step records
      * ``bug_events``             -- BUG_DETECTED events from this run
      * ``resolution_events``      -- BUG_RESOLVED events (filled by lifecycle)
      * ``insights``               -- derived from the truth (passes/fails
                                      are authoritative; counts only)
    """
    truth = evaluate_test_run({"results": list(results or [])})

    canonical_status = truth.get("overall_status")
    test_data["overall_status"] = "pass" if canonical_status == "PASS" else "fail"
    test_data["health_score"] = _truth_health_score(truth)
    test_data["scenario_results"] = truth.get("scenario_results") or []
    test_data["step_results"] = truth.get("step_results") or []
    test_data["bug_events"] = truth.get("bug_events") or []
    test_data["resolution_events"] = truth.get("resolution_events") or []

    # Insights are derived from the truth engine so they can never disagree
    # with overall_status. Critical/moderate/minor are simple counts.
    bug_events = truth.get("bug_events") or []
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for event in bug_events:
        sev = str(event.get("severity") or "low").lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    test_data["insights"] = {
        "critical": [event.get("error") or event.get("step_name") or "Failure" for event in bug_events if str(event.get("severity") or "").lower() == "high"],
        "moderate": [event.get("error") or event.get("step_name") or "Failure" for event in bug_events if str(event.get("severity") or "").lower() == "medium"],
        "minor": [event.get("error") or event.get("step_name") or "Failure" for event in bug_events if str(event.get("severity") or "").lower() == "low"],
    }

    # Summary counts use the canonical scenario roll-up.
    canonical_scenarios = truth.get("scenario_results") or []
    test_data["summary"] = dict(test_data.get("summary") or {})
    test_data["summary"]["total"] = len(canonical_scenarios)
    test_data["summary"]["passed"] = sum(1 for s in canonical_scenarios if s.get("status") == "PASS")
    test_data["summary"]["failed"] = sum(1 for s in canonical_scenarios if s.get("status") == "FAIL")
    test_data["summary"]["info"] = 0
    return truth


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _distinct_texts(values: List[Any]) -> List[str]:
    seen = set()
    distinct = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        distinct.append(text)
    return distinct


def _scenario_dependency_profile(scenario_case: TestCase) -> Dict[str, Any]:
    return {
        "depends_on": list(getattr(scenario_case, "depends_on", []) or []),
        "required_state": list(getattr(scenario_case, "required_state", []) or []),
        "produces_state": list(getattr(scenario_case, "produces_state", []) or []),
        "required_page": getattr(scenario_case, "required_page", None),
    }


def _scenario_dependency_key(scenario_case: TestCase) -> str:
    return str(
        getattr(scenario_case, "scenario_id", None)
        or getattr(scenario_case, "objective_id", None)
        or getattr(scenario_case, "title", None)
        or getattr(scenario_case, "scenario_name", None)
        or uuid.uuid4()
    )


def _topologically_order_scenarios(scenario_cases: List[TestCase]) -> List[TestCase]:
    pending = list(scenario_cases)
    ordered: List[TestCase] = []
    completed_states: set[str] = set()
    completed_keys: set[str] = set()
    safety_counter = 0

    while pending and safety_counter < len(pending) * 4:
        safety_counter += 1
        progressed = False
        for scenario_case in list(pending):
            dependency_profile = _scenario_dependency_profile(scenario_case)
            required_states = set(_normalize_text(state) for state in dependency_profile.get("required_state", []) if state)
            depends_on = set(_normalize_text(dep) for dep in dependency_profile.get("depends_on", []) if dep)
            if required_states.issubset(completed_states) and depends_on.issubset(completed_states.union(completed_keys)):
                ordered.append(scenario_case)
                pending.remove(scenario_case)
                completed_keys.add(_scenario_dependency_key(scenario_case))
                completed_states.update(_normalize_text(state) for state in dependency_profile.get("produces_state", []) if state)
                progressed = True
        if not progressed:
            ordered.extend(pending)
            break

    return ordered


def _dependency_guard_for_scenario(scenario_case: TestCase, shared_state: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    profile = _scenario_dependency_profile(scenario_case)
    current_states = {str(state).strip().lower() for state in shared_state.get("states", set())}
    current_keys = {str(key).strip().lower() for key in shared_state.get("completed_scenarios", set())}
    required_states = {str(state).strip().lower() for state in profile.get("required_state", []) if state}
    depends_on = {str(dep).strip().lower() for dep in profile.get("depends_on", []) if dep}
    required_page = str(profile.get("required_page") or "").strip().lower()
    current_page = str(shared_state.get("current_page") or shared_state.get("current_url") or "").strip().lower()
    current_title = str(shared_state.get("current_title") or "").strip().lower()
    authenticated = bool(shared_state.get("authenticated"))

    missing_states = sorted(required_states - current_states)
    missing_dependencies = sorted(depends_on - (current_states | current_keys))
    missing_page = bool(required_page) and required_page not in current_page and required_page not in current_title
    if required_page == "login" and current_page and any(domain in current_page for domain in {"saucedemo.com", "localhost", "127.0.0.1"}):
        missing_page = False
    missing_auth = bool(required_states and any("auth" in state or "login" in state for state in required_states) and not authenticated)

    if missing_states or missing_dependencies or missing_page or missing_auth:
        return False, {
            "missing_states": missing_states,
            "missing_dependencies": missing_dependencies,
            "missing_page": required_page if missing_page else None,
            "missing_auth": missing_auth,
            "required_page": required_page or None,
            "current_page": current_page or None,
            "current_title": current_title or None,
        }

    return True, {
        "missing_states": [],
        "missing_dependencies": [],
        "missing_page": None,
        "missing_auth": False,
        "required_page": required_page or None,
        "current_page": current_page or None,
        "current_title": current_title or None,
    }


def _update_shared_state_from_run(shared_state: Dict[str, Any], scenario_case: TestCase, scenario_run: Dict[str, Any]) -> Dict[str, Any]:
    next_state = copy.deepcopy(shared_state)
    artifacts = scenario_run.get("artifacts") if isinstance(scenario_run.get("artifacts"), dict) else {}
    if artifacts.get("storage_state"):
        next_state["storage_state"] = artifacts.get("storage_state")
    if artifacts.get("session_storage") is not None:
        next_state["session_storage"] = artifacts.get("session_storage") or {}
    next_state["previous_successful_actions"] = list(artifacts.get("previous_successful_actions") or [])
    next_state["authenticated"] = bool(artifacts.get("authenticated") or next_state.get("authenticated"))
    next_state["current_url"] = scenario_run.get("final_url") or scenario_run.get("url") or shared_state.get("current_url")
    next_state["current_page"] = next_state.get("current_url")
    next_state["current_title"] = scenario_run.get("page_title") or shared_state.get("current_title")
    next_state.setdefault("states", set())
    next_state.setdefault("completed_scenarios", set())
    next_state["completed_scenarios"].add(_scenario_dependency_key(scenario_case))
    next_state["states"].update(_normalize_text(state) for state in _scenario_dependency_profile(scenario_case).get("produces_state", []) if state)
    return next_state


def _discovery_workflow_entry(discovery: Dict[str, Any], scenario_case: TestCase) -> str:
    workflows = discovery.get("workflows") if isinstance(discovery.get("workflows"), list) else []
    pages = discovery.get("pages") if isinstance(discovery.get("pages"), list) else []
    feature_key = _normalize_text(getattr(scenario_case, "feature_key", None))
    objective_name = _normalize_text(getattr(scenario_case, "objective_name", None))
    title = _normalize_text(getattr(scenario_case, "title", None))

    if feature_key:
        for workflow in workflows:
            if _normalize_text(workflow.get("feature_key")) == feature_key:
                return str(workflow.get("entry_point") or workflow.get("url") or "").strip()

    keywords = [title, objective_name]
    for workflow in workflows:
        workflow_text = _normalize_text(workflow.get("name"))
        if any(keyword and keyword in workflow_text for keyword in keywords):
            return str(workflow.get("entry_point") or workflow.get("url") or "").strip()

    if workflows:
        return str(workflows[0].get("entry_point") or workflows[0].get("url") or "").strip()
    if pages:
        return str(pages[0].get("url") or "").strip()
    return ""


def _selector_candidates_from_dom(step: Dict[str, Any], dom: Dict[str, Any]) -> List[str]:
    action = _normalize_text(step.get("action"))
    step_text = _normalize_text(step.get("target") or step.get("selector") or step.get("value"))

    candidates: List[str] = []
    buttons = dom.get("buttons") if isinstance(dom.get("buttons"), list) else []
    links = dom.get("links") if isinstance(dom.get("links"), list) else []
    inputs = dom.get("inputs") if isinstance(dom.get("inputs"), list) else []
    headings = dom.get("headings") if isinstance(dom.get("headings"), list) else []

    if action in {"fill", "input", "type", "enter", "enter text", "input text"}:
        for field in inputs:
            candidates.extend(_distinct_texts([
                field.get("placeholder"),
                field.get("name"),
                field.get("id"),
                field.get("aria_label"),
            ]))

        if any(keyword in step_text for keyword in ["password"]):
            for field in inputs:
                field_text = _normalize_text(" ".join([
                    field.get("placeholder") or "",
                    field.get("name") or "",
                    field.get("id") or "",
                    field.get("type") or "",
                ]))
                if "password" in field_text:
                    candidates.insert(0, field.get("placeholder") or field.get("name") or field.get("id") or "")
                    break

        if any(keyword in step_text for keyword in ["email", "username", "user name", "login"]):
            for field in inputs:
                field_text = _normalize_text(" ".join([
                    field.get("placeholder") or "",
                    field.get("name") or "",
                    field.get("id") or "",
                    field.get("type") or "",
                ]))
                if any(keyword in field_text for keyword in ["email", "user", "login", "name"]):
                    candidates.insert(0, field.get("placeholder") or field.get("name") or field.get("id") or "")
                    break

    else:
        for button in buttons:
            candidates.extend(_distinct_texts([button.get("text"), button.get("aria_label"), button.get("name"), button.get("id")]))
        for link in links:
            candidates.extend(_distinct_texts([link.get("text")]))
        for heading in headings:
            candidates.extend(_distinct_texts([heading]))

    if step.get("target"):
        candidates.append(str(step.get("target")))
    if step.get("selector"):
        candidates.append(str(step.get("selector")))

    return _distinct_texts(candidates)


def _infer_scenario_failure_context(scenario_case: TestCase, step_results: List[Dict[str, Any]], scenario_run: Dict[str, Any]) -> Dict[str, Any]:
    failed_step = next((item for item in step_results if isinstance(item, dict) and str(item.get("status") or "").lower() == "fail"), None)
    validation = failed_step.get("validation") if isinstance(failed_step and failed_step.get("validation"), dict) else {}
    failure_category = str((failed_step or {}).get("failure_category") or scenario_run.get("failure_category") or "").strip().upper()
    root_cause = str((failed_step or {}).get("root_cause") or scenario_run.get("root_cause") or "").strip().upper()
    error_text = str((failed_step or {}).get("error") or (failed_step or {}).get("details") or scenario_run.get("error") or scenario_run.get("failure_reason") or "").strip()

    if not failure_category:
        failure_category = classify_failure_category(
            error_text=error_text,
            console_errors=validation.get("console_errors"),
            network_failures=validation.get("network_failures"),
            step_text=(failed_step or {}).get("test") or (failed_step or {}).get("step", {}).get("action") or "",
            selector=(failed_step or {}).get("selector_used") or (failed_step or {}).get("step", {}).get("selector") or "",
            target=(failed_step or {}).get("step", {}).get("target") or "",
            test_name=getattr(scenario_case, "title", "") or "",
            validation=validation,
        )

    if not root_cause:
        root_cause = classify_root_cause(
            action=(failed_step or {}).get("step", {}).get("action") or "",
            category=failure_category,
            error=error_text,
            console_errors=validation.get("console_errors"),
            network_failures=validation.get("network_failures"),
            selector_used=(failed_step or {}).get("selector_used") or (failed_step or {}).get("step", {}).get("selector") or "",
            validation=validation,
        ).get("root_cause", "UNKNOWN")

    if not error_text:
        error_text = failure_category or root_cause or "scenario_failure"

    return {
        "failure_reason": error_text,
        "failure_category": failure_category or "UNKNOWN",
        "root_cause": root_cause or "UNKNOWN",
        "failed_step": failed_step,
    }


def _build_recovery_strategy_plan(scenario_case: TestCase, failure_context: Dict[str, Any], dom: Dict[str, Any], discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
    root_cause = str(failure_context.get("root_cause") or "UNKNOWN").upper()
    failure_category = str(failure_context.get("failure_category") or "UNKNOWN").upper()
    strategy_order: List[str]

    if root_cause in {"ELEMENT_NOT_FOUND", "SELECTOR_CHANGED", "ELEMENT_NOT_VISIBLE"} or failure_category == "SELECTOR":
        strategy_order = ["alternate_selectors", "alternate_workflow_path", "alternate_navigation"]
    elif root_cause in {"NAVIGATION_REDIRECT", "TIMEOUT"} or failure_category in {"NAVIGATION", "TIMEOUT"}:
        strategy_order = ["alternate_navigation", "alternate_workflow_path", "alternate_selectors"]
    else:
        strategy_order = ["alternate_workflow_path", "alternate_selectors", "alternate_navigation"]

    return [{
        "strategy": strategy,
        "recovery_reason": root_cause if root_cause != "UNKNOWN" else failure_category,
        "entry_point": _discovery_workflow_entry(discovery, scenario_case) if strategy in {"alternate_workflow_path", "alternate_navigation"} else "",
        "selector_candidates": _selector_candidates_from_dom((failure_context.get("failed_step") or {}).get("step", {}) if isinstance(failure_context.get("failed_step"), dict) else {}, dom) if strategy in {"alternate_selectors", "alternate_workflow_path"} else [],
    } for strategy in strategy_order]


def _build_replanned_test_case(scenario_case: TestCase, recovery_plan: Dict[str, Any], dom: Dict[str, Any]) -> TestCase:
    payload = scenario_case.model_dump()
    payload["steps"] = [step.model_dump() for step in scenario_case.steps]
    steps: List[Dict[str, Any]] = payload["steps"]
    strategy = recovery_plan.get("strategy")
    selector_candidates = recovery_plan.get("selector_candidates") or []
    entry_point = str(recovery_plan.get("entry_point") or "").strip()

    if strategy == "alternate_selectors":
        for index, step in enumerate(steps):
            if str(step.get("action") or "").lower() in {"fill", "input", "type", "enter", "enter_text", "input_text", "click", "hover", "wait", "select", "verify"}:
                if selector_candidates:
                    step["target"] = selector_candidates[0]
                    if not step.get("selector"):
                        step["selector"] = ""
                    break

    elif strategy == "alternate_navigation" and entry_point:
        for step in steps:
            if str(step.get("action") or "").lower() == "navigate":
                step["value"] = entry_point
                break
        else:
            steps.insert(0, {
                "action": "navigate",
                "target": "alternate workflow entry point",
                "value": entry_point,
                "feature_key": scenario_case.feature_key,
                "objective_id": scenario_case.objective_id,
                "objective_name": scenario_case.objective_name,
                "scenario_id": scenario_case.scenario_id,
                "scenario_name": scenario_case.scenario_name,
                "coverage_level": scenario_case.coverage_level,
            })

    elif strategy == "alternate_workflow_path":
        if entry_point:
            if steps and str(steps[0].get("action") or "").lower() == "navigate":
                steps[0]["value"] = entry_point
            else:
                steps.insert(0, {
                    "action": "navigate",
                    "target": "workflow entry point",
                    "value": entry_point,
                    "feature_key": scenario_case.feature_key,
                    "objective_id": scenario_case.objective_id,
                    "objective_name": scenario_case.objective_name,
                    "scenario_id": scenario_case.scenario_id,
                    "scenario_name": scenario_case.scenario_name,
                    "coverage_level": scenario_case.coverage_level,
                })

        if selector_candidates:
            for step in steps:
                if str(step.get("action") or "").lower() in {"fill", "input", "type", "enter", "enter_text", "input_text", "click", "hover", "wait", "select", "verify"}:
                    step["target"] = selector_candidates[0]
                    if not step.get("selector"):
                        step["selector"] = ""
                    break

    payload["steps"] = steps
    payload["objective_id"] = scenario_case.objective_id
    payload["objective_name"] = scenario_case.objective_name
    payload["feature_key"] = scenario_case.feature_key
    payload["coverage_level"] = scenario_case.coverage_level
    payload["scenario_id"] = scenario_case.scenario_id
    payload["scenario_name"] = scenario_case.scenario_name
    return TestCase.model_validate(payload)


async def _run_scenario_with_replanning(url: str, scenario_case: TestCase, dom: Dict[str, Any], discovery: Dict[str, Any], progress_callback=None, shared_state: Dict[str, Any] | None = None, session_manager=None) -> Dict[str, Any]:
    recovery_history: List[Dict[str, Any]] = []
    current_case = scenario_case
    max_recovery_attempts = 3
    active_shared_state = copy.deepcopy(shared_state or {})

    for attempt_index in range(max_recovery_attempts + 1):
        results_data = await run_test_steps(url=url, test_case=current_case, dom=dom, progress_callback=progress_callback, shared_state=active_shared_state, session_manager=session_manager)
        step_results = results_data.get("results", [])
        run_status = str(results_data.get("run_status") or "").lower()

        if run_status in {"timed_out", "timeout", "cancelled"}:
            failure_context = _infer_scenario_failure_context(scenario_case, step_results, results_data)
            failure_context["failure_reason"] = failure_context.get("failure_reason") or results_data.get("failure_reason") or "scenario_timeout"
            failure_context["failure_category"] = failure_context.get("failure_category") or "TIMEOUT"
            failure_context["root_cause"] = failure_context.get("root_cause") or "TIMEOUT"
            return {
                "result": results_data,
                "step_results": step_results,
                "failure_context": failure_context,
                "recovery_history": recovery_history,
                "recovery_attempts": len(recovery_history),
                "recovery_strategy": {
                    "status": "timed_out",
                    "attempts": recovery_history,
                    "failure_reason": failure_context.get("failure_reason"),
                },
                "recovered": False,
                "shared_state": _update_shared_state_from_run(active_shared_state, scenario_case, results_data),
            }

        has_failure = any(item.get("status") == "fail" for item in step_results)

        if not has_failure and results_data.get("run_status") != "failed":
            failure_context = _infer_scenario_failure_context(scenario_case, step_results, results_data)
            return {
                "result": results_data,
                "step_results": step_results,
                "failure_context": failure_context,
                "recovery_history": recovery_history,
                "recovery_attempts": len(recovery_history),
                "recovery_strategy": {
                    "status": "not_needed" if not recovery_history else "recovered",
                    "attempts": recovery_history,
                },
                "recovered": bool(recovery_history),
                "shared_state": _update_shared_state_from_run(active_shared_state, scenario_case, results_data),
            }

        failure_context = _infer_scenario_failure_context(current_case, step_results, results_data)
        recovery_plan = _build_recovery_strategy_plan(current_case, failure_context, dom, discovery)
        failed_step = failure_context.get("failed_step") or {}
        original_step = failed_step.get("step") if isinstance(failed_step, dict) else None
        failed_step_action = ""
        if isinstance(failed_step, dict):
            failed_step_action = str((failed_step.get("step") or {}).get("action") or "")

        for strategy_index, strategy_plan in enumerate(recovery_plan, start=1):
            recovery_record = {
                "attempt": len(recovery_history) + 1,
                "replan_attempt": len(recovery_history) + 1,
                "strategy": strategy_plan.get("strategy"),
                "recovery_reason": strategy_plan.get("recovery_reason"),
                "replan_reason": strategy_plan.get("recovery_reason"),
                "failure_reason": failure_context.get("failure_reason"),
                "failed_step_action": failed_step_action,
                "original_step": original_step,
                "entry_point": strategy_plan.get("entry_point"),
                "selector_candidates": strategy_plan.get("selector_candidates"),
                "status": "pending",
                "replan_result": "pending",
            }
            recovery_history.append(recovery_record)

            if progress_callback:
                await progress_callback(
                    {
                        "type": "scenario_recovery_attempt",
                        "message": f"Replanning scenario with {strategy_plan.get('strategy')}",
                        "scenario_id": scenario_case.scenario_id,
                        "scenario_name": scenario_case.scenario_name,
                        "objective_id": scenario_case.objective_id,
                        "objective_name": scenario_case.objective_name,
                        "failure_reason": failure_context.get("failure_reason"),
                        "recovery_strategy": strategy_plan.get("strategy"),
                        "recovery_attempts": len(recovery_history),
                        "recovery_plan": strategy_plan,
                    }
                )

            current_case = _build_replanned_test_case(scenario_case, strategy_plan, dom)
            recovery_result = await run_test_steps(url=url, test_case=current_case, dom=dom, progress_callback=progress_callback, shared_state=active_shared_state, session_manager=session_manager)
            recovery_step_results = recovery_result.get("results", [])
            recovery_failed = any(item.get("status") == "fail" for item in recovery_step_results) or recovery_result.get("run_status") == "failed"
            recovery_record["status"] = "failed" if recovery_failed else "passed"
            recovery_record["result_status"] = recovery_result.get("run_status")
            recovery_record["replan_result"] = {
                "status": "failed" if recovery_failed else "passed",
                "run_status": recovery_result.get("run_status"),
                "recovered": not recovery_failed,
            }

            if not recovery_failed:
                success_context = _infer_scenario_failure_context(current_case, recovery_step_results, recovery_result)
                return {
                    "result": recovery_result,
                    "step_results": recovery_step_results,
                    "failure_context": failure_context,
                    "recovery_history": recovery_history,
                    "recovery_attempts": len(recovery_history),
                    "recovery_strategy": {
                        "status": "recovered",
                        "selected_strategy": strategy_plan.get("strategy"),
                        "attempts": recovery_history,
                        "failure_reason": failure_context.get("failure_reason"),
                        "final_context": success_context,
                    },
                    "recovered": True,
                }

    return {
        "result": results_data,
        "step_results": step_results,
        "failure_context": failure_context,
        "recovery_history": recovery_history,
        "recovery_attempts": len(recovery_history),
        "recovery_strategy": {
            "status": "exhausted",
            "attempts": recovery_history,
            "failure_reason": failure_context.get("failure_reason"),
        },
        "replan_history": recovery_history,
        "recovered": False,
    }

def create_test_run(req: TestRequest, user_id: str):
    test_id = str(uuid.uuid4())

    test_data = {
        "user_id": user_id,
        "execution_id": test_id,
        "test_id": test_id,
        "url": _canonicalize_url(req.url),
        "target_url": _canonicalize_url(req.url),
        "test_name": req.test_name,
        "name": req.test_name,
        "project": req.project_name,
        "test_type": req.test_type,
        "browser": req.browser,
        "device": req.device,
        "coverage_level": req.coverage_level,
        "execution_settings": req.execution_settings,
        "status": "running",
        "results": [],
        "stream_logs": [],
        "screenshot": None,
        "summary": None,
        "health_score": None,
        "overall_status": None,
        "insights": None,
        "priority_issues": [],
        "recommendations": [],
        "report": None,
        "ai_summary": None,
        "bugs": [],
        "discovery_status": "pending",
        "discovery_error": None,
        "risk_summary": {},
        "scenario_tree": {},
        "ai_plan": req.ai_plan,
        "created_at": datetime.utcnow().isoformat()
    }

    collection.insert_one(test_data)
    db["artifacts"].insert_one({
        "user_id": user_id,
        "execution_id": test_id,
        "test_id": test_id,
        "kind": "test_run",
        "created_at": datetime.utcnow().isoformat(),
    })

    return test_data

def run_test_and_update(test_data, url, user_id: str):
    """Legacy synchronous entry point used when ``ai_plan`` is empty.

    The order of writes follows the same invariant as the async variant:

      1. Compute the terminal status from results.
      2. Write the terminal status UNCONDITIONALLY (no status guard).
      3. Best-effort: create bugs, save report.
    """
    from backend.services.execution_watchdog import _force_terminal

    results: list = []
    artifacts: dict = {}
    try:
        results, artifacts = run_test(url, test_data["test_id"], user_id=user_id)
        artifacts = _tokenize_artifact_urls(artifacts, user_id)
        test_data["results"] = results
        test_data["artifacts"] = artifacts
        test_data["status"] = "completed_with_failures" if any(item.get("status") == "fail" for item in results) else "completed"
    except Exception as e:
        test_data["status"] = "failed"
        test_data["results"] = [{"error": str(e)}]
        test_data["failure_reason"] = "legacy_execution_exception"
        test_data["summary"] = None
        test_data["health_score"] = 0
        test_data["ai_summary"] = "Test execution failed."

    # Scoring (best effort)
    try:
        score_data = calculate_health_score(results or [])
        test_data["summary"] = score_data["summary"]
        test_data["health_score"] = score_data["score"]
    except Exception:
        test_data.setdefault("summary", None)
        test_data.setdefault("health_score", 0)

    if isinstance(test_data.get("summary"), dict):
        test_data["summary"].update(_collect_recovery_summary(results or []))
        failed_tasks = sum(1 for item in (results or []) if item.get("status") == "fail")
        completed_tasks = sum(1 for item in (results or []) if item.get("status") in {"pass", "completed"})
        test_data["summary"]["total_tasks"] = len(results or [])
        test_data["summary"]["completed_tasks"] = completed_tasks
        test_data["summary"]["successful_tasks"] = completed_tasks
        test_data["summary"]["failed_tasks"] = failed_tasks
        test_data["summary"]["skipped_tasks"] = 0

    try:
        # Truth engine is the single source of truth. It returns the
        # canonical overall_status, health_score, scenario_results, and
        # bug_events in one shot. The legacy insights / recommendations
        # / report / ai_summary helpers consume the truth-engine output
        # so they cannot drift from it.
        truth = _apply_truth_engine(test_data, results)
        insights = test_data.get("insights") or {}
        test_data["recommendations"] = generate_recommendations(insights)
        test_data["report"] = generate_report(test_data.get("health_score", 0), test_data.get("summary"), insights)
        test_data["ai_summary"] = generate_summary_line(test_data.get("health_score", 0), test_data.get("summary"), insights)
        test_data["bug_events"] = truth.get("bug_events") or []
    except Exception:
        logger.exception("Legacy scoring pipeline failed for test_id=%s", test_data.get("test_id"))

    screenshot_urls = []
    for path in (artifacts.get("screenshots") or []):
        filename = os.path.basename(path)
        screenshot_urls.append(build_artifact_url(user_id, f"artifacts/{test_data['test_id']}/{filename}"))

    test_data["ai_report"] = {
        "user_id": user_id,
        "execution_id": test_data["test_id"],
        "website_health_score": test_data.get("health_score", 0),
        "workflow_completion": test_data.get("overall_status"),
        "critical_issues": len((test_data.get("insights") or {}).get("critical", [])),
        "warnings": len((test_data.get("insights") or {}).get("moderate", [])) + len((test_data.get("insights") or {}).get("minor", [])),
        "screenshots": screenshot_urls,
        "report": test_data.get("report", ""),
        "insights": test_data.get("insights", {}),
        "recovery_summary": _collect_recovery_summary(results or []),
        "run_status": test_data.get("status"),
    }
    test_data["screenshot_paths"] = screenshot_urls

    # ---- GUARANTEED TERMINAL WRITE (unconditional) ----
    # Use the sync _force_terminal helper which has no status guard. Bugs and
    # report are written best-effort and are allowed to fail without
    # affecting the terminal state.
    try:
        # Run the async terminal write in a fresh event loop so we don't
        # conflict with the calling thread's loop.  ``asyncio.run`` is safe
        # here because this function is invoked from ``asyncio.to_thread``
        # in the legacy task path.
        import asyncio as _asyncio
        from backend.services.execution_watchdog import enforce_terminal_write

        async def _do_terminal_write() -> None:
            async def _bugs():
                try:
                    create_bugs_from_test(test_data)
                except Exception:
                    logger.exception("Legacy create_bugs failed for test_id=%s", test_data.get("test_id"))

            async def _reconcile():
                try:
                    reconcile_bugs_on_passing_run(test_data)
                except Exception:
                    logger.exception("Legacy reconcile_bugs failed for test_id=%s", test_data.get("test_id"))

            async def _save():
                try:
                    save_report(
                        test_data,
                        report_type="legacy",
                        user_id=user_id,
                        test_run_id=test_data["test_id"],
                        title=test_data.get("project") or test_data.get("test_name") or test_data["test_id"],
                        summary=test_data.get("ai_summary") or test_data.get("report") or "Legacy test execution report.",
                        status=test_data.get("status"),
                    )
                except Exception:
                    logger.exception("Legacy save_report failed for test_id=%s", test_data.get("test_id"))

            await enforce_terminal_write(
                test_id=test_data["test_id"],
                user_id=user_id,
                payload=test_data,
                save_report_fn=_save,
                create_bugs_fn=_bugs,
                reconcile_bugs_fn=_reconcile,
            )

        try:
            _asyncio.run(_do_terminal_write())
        except RuntimeError:
            # Already inside an event loop — fall back to direct writes.
            _force_terminal_sync(test_id=test_data["test_id"], user_id=user_id, payload=test_data)
            try:
                create_bugs_from_test(test_data)
            except Exception:
                logger.exception("Legacy create_bugs failed for test_id=%s", test_data.get("test_id"))
            try:
                reconcile_bugs_on_passing_run(test_data)
            except Exception:
                logger.exception("Legacy reconcile_bugs failed for test_id=%s", test_data.get("test_id"))
            try:
                save_report(
                    test_data,
                    report_type="legacy",
                    user_id=user_id,
                    test_run_id=test_data["test_id"],
                    title=test_data.get("project") or test_data.get("test_name") or test_data["test_id"],
                    summary=test_data.get("ai_summary") or test_data.get("report") or "Legacy test execution report.",
                    status=test_data.get("status"),
                )
            except Exception:
                logger.exception("Legacy save_report failed for test_id=%s", test_data.get("test_id"))
    except Exception:
        logger.exception("Legacy terminal write crashed for test_id=%s", test_data.get("test_id"))
        try:
            collection.update_one(
                {"test_id": test_data["test_id"], "user_id": user_id},
                {"$set": test_data},
                upsert=True,
            )
        except Exception:
            logger.exception("Fallback legacy terminal write failed for test_id=%s", test_data.get("test_id"))


def _force_terminal_sync(test_id: str, user_id: str, payload: dict) -> None:
    """Sync version of watchdog._force_terminal."""
    from datetime import datetime as _dt, timezone as _tz
    safe = dict(payload)
    safe.setdefault("updated_at", _dt.now(_tz.utc).isoformat())
    try:
        collection.update_one(
            {"test_id": test_id, "user_id": user_id},
            {"$set": safe},
            upsert=True,
        )
    except Exception:
        logger.exception("_force_terminal_sync: write failed for test_id=%s", test_id)


def _tokenize_artifact_urls(node: Any, user_id: str) -> Any:
    if isinstance(node, dict):
        return {key: _tokenize_artifact_urls(value, user_id) for key, value in node.items()}
    if isinstance(node, list):
        return [_tokenize_artifact_urls(item, user_id) for item in node]
    if isinstance(node, str) and node.startswith("/screenshots/") and "token=" not in node:
        return build_screenshot_url(user_id, node.lstrip("/"))
    if isinstance(node, str) and node.startswith("/artifacts/") and "token=" not in node:
        return build_artifact_url(user_id, node.lstrip("/"))
    return node


def _flatten_plan_results(plan_results: List[Dict[str, Any]], case_title: str) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for index, step_result in enumerate(plan_results, start=1):
        step = step_result.get("step", {}) if isinstance(step_result, dict) else {}
        validation = step_result.get("validation") if isinstance(step_result, dict) and isinstance(step_result.get("validation"), dict) else {}
        failure_category = str(step_result.get("failure_category") or "").strip().upper()
        root_cause = str(step_result.get("root_cause") or "").strip().upper()
        root_cause_confidence = step_result.get("root_cause_confidence")
        if step_result.get("status") == "failed" and failure_category not in {"AUTHENTICATION", "NAVIGATION", "SELECTOR", "NETWORK", "CONSOLE", "TIMEOUT", "VALIDATION", "UNKNOWN"}:
            failure_category = classify_failure_category(
                error_text=step_result.get("error") or step_result.get("details") or "",
                console_errors=validation.get("console_errors"),
                network_failures=validation.get("network_failures"),
                step_text=f"{case_title} {step.get('action') or ''} {step.get('target') or ''}",
                selector=step.get("selector") or "",
                target=step.get("target") or "",
                test_name=case_title,
                validation=validation,
            )
        if step_result.get("status") == "failed" and root_cause not in {"SELECTOR_CHANGED", "ELEMENT_NOT_VISIBLE", "ELEMENT_NOT_FOUND", "NAVIGATION_REDIRECT", "NETWORK_FAILURE", "API_FAILURE", "AUTHENTICATION_FAILURE", "TIMEOUT", "PAGE_CRASH", "JAVASCRIPT_ERROR", "UNKNOWN"}:
            root_cause_data = classify_root_cause(
                action=step.get("action") or case_title,
                category=failure_category,
                error=step_result.get("error") or step_result.get("details") or "",
                console_errors=validation.get("console_errors"),
                network_failures=validation.get("network_failures"),
                selector_used=step.get("selector") or "",
                validation=validation,
            )
            root_cause = str(root_cause_data["root_cause"]).upper()
            root_cause_confidence = root_cause_data["confidence"]
        flattened.append({
            "test": f"{case_title} - Step {index}",
            "status": "pass" if step_result.get("status") != "failed" else "fail",
            "details": step_result.get("error") or step_result.get("validation") or step.get("action") or "AI step executed",
            "objective_id": step.get("objective_id"),
            "objective_name": step.get("objective_name"),
            "scenario_id": step.get("scenario_id"),
            "scenario_name": step.get("scenario_name"),
            "coverage_level": step.get("coverage_level"),
            "validation": validation,
            "failure_category": failure_category if step_result.get("status") == "failed" else None,
            "root_cause": root_cause if step_result.get("status") == "failed" else None,
            "root_cause_confidence": root_cause_confidence if step_result.get("status") == "failed" else None,
            "recovery_attempted": bool(step_result.get("recovery_attempted")),
            "recovery_type": step_result.get("recovery_type") or None,
            "recovery_success": bool(step_result.get("recovery_success")),
            "recovery_actions": step_result.get("recovery_actions", []),
            "recovery_error": step_result.get("recovery_error"),
            "recovery_hint": step_result.get("recovery_hint"),
        })
    return flattened


def _validate_plan_objectives(plan: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    requested = plan.get("requested_objectives") if isinstance(plan.get("requested_objectives"), list) else []
    planned = plan.get("planned_objectives") if isinstance(plan.get("planned_objectives"), list) else []
    objective_tracking = plan.get("objective_tracking") if isinstance(plan.get("objective_tracking"), list) else []
    metrics = plan.get("plan_metrics") if isinstance(plan.get("plan_metrics"), dict) else {}
    scenario_cap_applied = bool(metrics.get("scenario_cap_applied"))

    requested_count = int(metrics.get("requested_objectives", len(requested)) or len(requested))
    planned_count = int(metrics.get("planned_objectives", len(planned) or len(objective_tracking)) or len(planned) or len(objective_tracking))
    generated_steps = int(metrics.get("generated_steps", 0) or 0)
    generated_scenarios = int(metrics.get("generated_scenarios", sum(int(item.get("generated_scenarios", 0) or 0) for item in objective_tracking)) or 0)

    test_case_steps = ((plan.get("test_case") or {}).get("steps") or []) if isinstance(plan.get("test_case"), dict) else []
    legacy_single_plan = not requested and not planned and not objective_tracking and isinstance(test_case_steps, list) and len(test_case_steps) > 0

    has_required_lists = requested_count > 0 and planned_count > 0 and bool(objective_tracking)
    coverage_match = requested_count == planned_count
    tracking_steps_valid = all(int(item.get("generated_steps", 0) or 0) > 0 for item in objective_tracking)
    tracking_scenarios_valid = all(int(item.get("generated_scenarios", 0) or 0) > 0 for item in objective_tracking)
    if scenario_cap_applied:
        tracking_steps_valid = any(int(item.get("generated_steps", 0) or 0) > 0 for item in objective_tracking)
        tracking_scenarios_valid = any(int(item.get("generated_scenarios", 0) or 0) > 0 for item in objective_tracking)
    valid = (has_required_lists and coverage_match and tracking_steps_valid and tracking_scenarios_valid and generated_steps > 0 and generated_scenarios > 0) or legacy_single_plan

    payload = {
        "requested_objectives": requested_count if not legacy_single_plan else 1,
        "planned_objectives": planned_count if not legacy_single_plan else 1,
        "generated_steps": generated_steps if not legacy_single_plan else len(test_case_steps),
        "generated_scenarios": generated_scenarios if not legacy_single_plan else 1,
        "requested_objective_names": requested if not legacy_single_plan else ["Legacy Workflow"],
        "planned_objective_names": (planned or [item.get("objective_name") for item in objective_tracking]) if not legacy_single_plan else ["Legacy Workflow"],
        "scenario_cap_applied": scenario_cap_applied,
        "legacy_plan": legacy_single_plan,
    }
    return valid, payload


def _build_objective_coverage(objective_tracking: List[Dict[str, Any]], flattened_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    for objective in objective_tracking:
        objective_id = str(objective.get("objective_id") or "").strip()
        if not objective_id:
            continue
        stats[objective_id] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "name": objective.get("objective_name") or objective_id,
            "feature_key": objective.get("feature_key"),
            "coverage_level": objective.get("coverage_level"),
            "coverage_profile": objective.get("coverage_profile"),
            "priority_score": int(objective.get("priority_score", 0) or 0),
            "risk_score": int(objective.get("risk_score", 0) or 0),
            "risk_level": objective.get("risk_level"),
            "critical": bool(
                objective.get("critical")
                or objective.get("is_critical")
                or str(objective.get("coverage_level") or "").upper() == "SECURITY"
                or str(objective.get("feature_key") or "").upper() in {"LOGIN", "CHECKOUT", "PAYMENT", "CART", "AUTH", "AUTHENTICATION", "INVENTORY"}
            ),
            "scenarios": {},
        }

    for result in flattened_results:
        objective_id = str(result.get("objective_id") or "").strip()
        if not objective_id or objective_id not in stats:
            continue
        stats[objective_id]["total"] += 1
        scenario_id = str(result.get("scenario_id") or "").strip()
        scenario_name = str(result.get("scenario_name") or "").strip() or scenario_id
        if scenario_id:
            scenario_stats = stats[objective_id]["scenarios"].setdefault(
                scenario_id,
                {
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_name,
                    "generated_steps": int(result.get("generated_steps", 0) or 0),
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                },
            )
            scenario_stats["total"] += 1
            if result.get("status") == "fail":
                scenario_stats["failed"] += 1
            else:
                scenario_stats["passed"] += 1

        if result.get("status") == "fail":
            stats[objective_id]["failed"] += 1
        else:
            stats[objective_id]["passed"] += 1

    objective_coverage: List[Dict[str, Any]] = []
    for objective in objective_tracking:
        objective_id = str(objective.get("objective_id") or "").strip()
        summary = stats.get(
            objective_id,
            {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "name": objective.get("objective_name") or objective_id,
                "feature_key": objective.get("feature_key"),
                "coverage_level": objective.get("coverage_level"),
                "coverage_profile": objective.get("coverage_profile"),
                "priority_score": int(objective.get("priority_score", 0) or 0),
                "risk_score": int(objective.get("risk_score", 0) or 0),
                "risk_level": objective.get("risk_level"),
                "critical": bool(objective.get("critical", False)),
                "scenarios": {},
            },
        )
        scenario_tracking = objective.get("scenarios") if isinstance(objective.get("scenarios"), list) else []
        scenario_rows: List[Dict[str, Any]] = []
        for scenario in scenario_tracking:
            scenario_id = str(scenario.get("scenario_id") or "").strip()
            scenario_stats = summary["scenarios"].get(
                scenario_id,
                {
                    "scenario_id": scenario_id,
                    "scenario_name": scenario.get("scenario_name") or scenario_id,
                    "generated_steps": int(scenario.get("generated_steps", 0) or 0),
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                },
            )
            scenario_rows.append(
                {
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_stats["scenario_name"],
                    "generated_steps": int(scenario_stats.get("generated_steps", scenario.get("generated_steps", 0)) or 0),
                    "coverage_level": scenario.get("coverage_level"),
                    "risk_score": int(scenario.get("risk_score", 0) or 0),
                    "risk_level": scenario.get("risk_level"),
                    "executed_steps": scenario_stats["total"],
                    "passed_steps": scenario_stats["passed"],
                    "failed_steps": scenario_stats["failed"],
                    "execution_status": "completed" if scenario_stats["total"] > 0 and scenario_stats["failed"] == 0 else "failed",
                }
            )

        execution_status = "completed" if summary["total"] > 0 and summary["failed"] == 0 else "failed"
        objective_coverage.append(
            {
                "objective_id": objective_id,
                "objective_name": summary["name"],
                "feature_key": summary.get("feature_key"),
                "coverage_level": summary.get("coverage_level"),
                "coverage_profile": summary.get("coverage_profile"),
                "priority_score": int(summary.get("priority_score", 0) or 0),
                "risk_score": int(summary.get("risk_score", 0) or 0),
                "risk_level": summary.get("risk_level"),
                "critical": bool(summary.get("critical", False)),
                "generated_steps": int(objective.get("generated_steps", 0) or 0),
                "generated_scenarios": int(objective.get("generated_scenarios", 0) or 0),
                "executed_scenarios": summary["total"],
                "passed_scenarios": summary["passed"],
                "failed_scenarios": summary["failed"],
                "execution_status": execution_status,
                "scenarios": scenario_rows,
            }
        )

    return objective_coverage


def _normalize_step_status(raw_status: Any) -> str:
    """Normalize a step-level status to the API contract: passed | failed | warning.

    The execution engine emits both legacy ("pass"/"fail") and current
    ("passed"/"failed") spellings, plus ad-hoc values like "skipped", "info"
    and "warning". The UI relies on a stable three-value contract so that
    per-step badges and the test history detail page can render reliably.
    """
    value = str(raw_status or "").strip().lower()
    if value in {"pass", "passed", "completed", "success", "ok"}:
        return "passed"
    if value in {"fail", "failed", "error", "broken"}:
        return "failed"
    if value == "warning":
        return "warning"
    return "warning"


def _build_step_api_entry(step_result: Dict[str, Any], step_index: int) -> Dict[str, Any]:
    """Project a raw step_result into the safe API contract shape.

    The raw step_result from execution_service contains a great deal of
    internal metadata (selector_used, recovery_actions, execution_context,
    validation dict, etc.) that the UI does not need. This projection keeps
    only the fields the test history page needs while still being permissive
    enough that future additions do not break the contract.
    """
    if not isinstance(step_result, dict):
        return {
            "step_index": step_index,
            "step_name": f"Step {step_index}",
            "status": "warning",
            "error": None,
            "details": None,
            "duration_ms": None,
        }

    step_meta = step_result.get("step") if isinstance(step_result.get("step"), dict) else {}
    action = step_meta.get("action") or step_result.get("test") or ""
    target = step_meta.get("target") or step_meta.get("selector") or step_result.get("selector_used") or ""
    step_name = f"{action} {target}".strip() if (action or target) else f"Step {step_index}"

    error_text = step_result.get("error") or step_result.get("recovery_error") or None
    details_text = step_result.get("details") or step_result.get("recovery_hint") or None
    if step_result.get("status") == "failed" and not error_text and not details_text:
        details_text = "Step failed"

    status = _normalize_step_status(step_result.get("status"))

    validation = step_result.get("validation") if isinstance(step_result.get("validation"), dict) else {}
    duration_ms = validation.get("duration_ms") if isinstance(validation.get("duration_ms"), (int, float)) else None

    return {
        "step_index": step_index,
        "step_name": step_name[:200] if isinstance(step_name, str) else f"Step {step_index}",
        "status": status,
        "error": error_text,
        "details": details_text,
        "duration_ms": duration_ms,
    }


def _build_scenario_result(
    step_results: List[Dict[str, Any]],
    scenario_case: TestCase,
    scenario_status: str,
    *,
    error: str | None = None,
    failure_reason: str | None = None,
    failure_category: str | None = None,
    root_cause: str | None = None,
    recovery_strategy: Dict[str, Any] | None = None,
    recovery_attempts: int = 0,
    recovery_history: List[Dict[str, Any]] | None = None,
    recovered: bool = False,
    dependency_guard: Dict[str, Any] | None = None,
    runtime_ms: float | None = None,
) -> Dict[str, Any]:
    passed_steps = sum(1 for item in step_results if item.get("status") != "fail")
    failed_steps = sum(1 for item in step_results if item.get("status") == "fail")
    skipped_steps = sum(1 for item in step_results if item.get("status") == "skipped")
    selector_fallback_count = sum(1 for item in step_results if item.get("selector_fallback_used"))
    verification_mismatch_count = sum(1 for item in step_results if item.get("verification_mismatch"))
    failed_step = next((item for item in step_results if item.get("status") == "fail"), None)
    original_step = failed_step.get("step") if isinstance(failed_step, dict) else None
    replan_attempts = list(recovery_history or [])
    is_failure_status = scenario_status in {"failed", "timed_out", "cancelled"}

    expected_steps = len(getattr(scenario_case, "steps", None) or [])
    executed_steps = sum(
        1 for item in step_results
        if item.get("status") in {"pass", "passed", "completed", "fail", "failed"}
    )
    incomplete_execution = expected_steps > 0 and executed_steps < expected_steps

    if incomplete_execution and not is_failure_status:
        is_failure_status = True
        if not failure_reason:
            failure_reason = f"incomplete_execution: {executed_steps}/{expected_steps} steps completed"
        if not failure_category:
            failure_category = "INCOMPLETE"
        if not root_cause:
            root_cause = "INCOMPLETE_EXECUTION"

    safe_step_results = [
        _build_step_api_entry(item, index)
        for index, item in enumerate(step_results or [], start=1)
    ]

    return {
        "test": scenario_case.title or scenario_case.scenario_name or scenario_case.objective_name or "Scenario",
        "status": "fail" if is_failure_status else "pass",
        "details": error or scenario_case.expected or ("Scenario recovered after replanning" if recovered else "Scenario executed"),
        "objective_id": scenario_case.objective_id,
        "objective_name": scenario_case.objective_name,
        "scenario_id": scenario_case.scenario_id,
        "scenario_name": scenario_case.scenario_name or scenario_case.title,
        "feature_key": getattr(scenario_case, "feature_key", None),
        "coverage_level": getattr(scenario_case, "coverage_level", None),
        "generated_steps": expected_steps or len(step_results),
        "executed_steps": executed_steps,
        "skipped_steps": skipped_steps,
        "passed_steps": passed_steps,
        "failed_steps": failed_steps,
        "step_results": safe_step_results,
        "original_step": original_step,
        "failure_reason": failure_reason or error,
        "failure_category": failure_category,
        "root_cause": root_cause,
        "recovery_strategy": recovery_strategy or {},
        "recovery_attempts": recovery_attempts,
        "recovery_history": recovery_history or [],
        "recovery_success": recovered,
        "replan_attempts": replan_attempts,
        "replan_result": recovery_strategy.get("status") if isinstance(recovery_strategy, dict) else None,
        "dependency_guard": dependency_guard or {},
        "selector_fallback_count": selector_fallback_count,
        "verification_mismatch_count": verification_mismatch_count,
        "runtime_ms": runtime_ms,
    }


async def run_ai_plan_and_update(test_data: Dict[str, Any], url: str, user_id: str, plan: Dict[str, Any]):
    from backend.services.execution_watchdog import (
        ProgressWatchdog,
        WatchdogTimer,
        enforce_terminal_write,
        is_terminal,
    )

    overall_started = perf_counter()
    test_id = test_data.get("test_id", "unknown")
    watchdog = ProgressWatchdog(test_id)
    watchdog_timer: Optional[WatchdogTimer] = None
    try:
        watchdog_timer = WatchdogTimer.start(
            asyncio.get_event_loop(),
            test_id=test_id,
            user_id=user_id,
            stall_seconds=int(os.getenv("EXECUTION_STALL_SECONDS", "300")),
        )
    except Exception:
        logger.exception("WatchdogTimer failed to start for test_id=%s; continuing without", test_id)

    try:
        # Normalize minimal expected test_data fields to avoid downstream KeyErrors
        if not test_data.get("url"):
            test_data["url"] = _canonicalize_url(url)
        test_data["target_url"] = _canonicalize_url(test_data.get("target_url") or test_data.get("url") or url)
        is_valid_plan, plan_validation_payload = _validate_plan_objectives(plan)
        if not is_valid_plan:
            test_data["status"] = "failed"
            test_data["failure_reason"] = "objective_planning_incomplete"
            test_data["results"] = []
            test_data["plan_metrics"] = plan_validation_payload
            test_data["objective_coverage"] = []
            test_data["ai_summary"] = "Planning failed: generated objectives do not fully cover requested objectives."
            test_data["stream_logs"] = [
                {
                    "time": datetime.utcnow().isoformat(),
                    "level": "error",
                    "msg": "Planning failed before execution: generated_objectives != requested_objectives",
                    "type": "planning_error",
                    "details": {
                        "failure_reason": "objective_planning_incomplete",
                        **plan_validation_payload,
                    },
                },
                {
                    "time": datetime.utcnow().isoformat(),
                    "level": "error",
                    "msg": (
                        "[ERROR] Test execution failed\n"
                        "  Reason          : Planning validation failed\n"
                        f"  Duration        : {round(perf_counter() - overall_started, 2)}s"
                    ),
                    "type": "terminal_summary",
                    "details": {
                        "final_status": "failed",
                        "error": "objective_planning_incomplete",
                        "duration_seconds": round(perf_counter() - overall_started, 2),
                    },
                },
            ]
            collection.update_one(
                {
                    "test_id": test_data["test_id"],
                    "user_id": user_id,
                    "status": {"$in": ["running", "cancel_requested"]},
                },
                {"$set": test_data},
                upsert=True,
            )
            return test_data


        plan_case = plan.get("test_case") or {}
        plan_title = plan_case.get("title") or "AI Feature Suite"
        test_cases_data = plan.get("test_cases") if isinstance(plan.get("test_cases"), list) and plan.get("test_cases") else [plan_case]
        scenario_cases = [TestCase.model_validate(case) for case in test_cases_data]
        scenario_cases = _topologically_order_scenarios(scenario_cases)
        translation_logs: List[Dict[str, Any]] = []
        scenario_results: List[Dict[str, Any]] = []
        overall_timed_out = False
        shared_state: Dict[str, Any] = {
            "states": set(),
            "completed_scenarios": set(),
            "current_url": url,
            "current_page": url,
            "current_title": "",
            "authenticated": False,
            "previous_successful_actions": [],
        }

        test_data["raw_ai_plan"] = plan_case
        test_data["normalized_ai_plan"] = {
            "title": plan_title,
            "expected": plan_case.get("expected") or "Execute all requested objectives with continue-on-failure behavior.",
            "scenarios": [case.model_dump() for case in scenario_cases],
        }
        test_data["plan_metrics"] = plan_validation_payload
        test_data["discovery"] = plan.get("discovery") or {"feature_map": [], "workflows": [], "forms": [], "pages": []}
        test_data["discovery_status"] = plan.get("discovery_status") or ("ready" if test_data["discovery"].get("feature_map") else "partial")
        test_data["discovery_error"] = plan.get("discovery_error")
        test_data["scenario_tree"] = plan.get("scenario_tree") or {}
        dom = await extract_page_elements(url)
        stream_logs: List[Dict[str, Any]] = []
        screenshot_paths: List[str] = []

        def _persist_partial_state(status: str = "running", failure_reason: str | None = None) -> None:
            test_data["results"] = list(scenario_results)
            test_data["stream_logs"] = list(stream_logs)
            test_data["screenshot_paths"] = list(screenshot_paths)
            test_data["status"] = status
            if failure_reason:
                test_data["failure_reason"] = failure_reason
            collection.update_one(
                {
                    "test_id": test_data["test_id"],
                    "user_id": user_id,
                    "status": {"$in": ["running", "cancel_requested"]},
                },
                {
                    "$set": {
                        "results": list(scenario_results),
                        "stream_logs": list(stream_logs),
                        "screenshot_paths": list(screenshot_paths),
                        "status": status,
                        **({"failure_reason": failure_reason} if failure_reason else {}),
                    }
                },
                upsert=True,
            )

        def _track_screenshot_path(raw: str) -> None:
            if not raw:
                return
            normalized = raw if raw.startswith("/") else f"/{raw.lstrip('/')}"
            if normalized not in screenshot_paths:
                screenshot_paths.append(normalized)

        async def progress_callback(event: Dict[str, Any]) -> None:
            # Always touch the watchdog so a stall (no progress events) is detected.
            watchdog.heartbeat(
                scenario_id=event.get("scenario_id"),
                scenario_name=event.get("scenario_name"),
            )
            # Handle screenshot payloads specially: persist to artifacts and
            # replace base64 payload with a file path for downstream reports.
            evt = dict(event)
            if evt.get("type") == "screenshot" and evt.get("screenshot_b64"):
                try:
                    folder = f"artifacts/{test_data['test_id']}"
                    os.makedirs(folder, exist_ok=True)
                    filename = f"step-{len(stream_logs)+1}-{int(datetime.utcnow().timestamp()*1000)}.png"
                    path = os.path.join(folder, filename)
                    with open(path, "wb") as fh:
                        fh.write(base64.b64decode(evt.get("screenshot_b64")))
                    # Replace payload with a reference URL path used by frontend
                    evt["screenshot"] = build_artifact_url(user_id, f"artifacts/{test_data['test_id']}/{filename}")
                    _track_screenshot_path(evt["screenshot"])
                    # remove the heavy base64 content
                    evt.pop("screenshot_b64", None)
                except Exception as e:
                    evt["screenshot_error"] = str(e)
            elif isinstance(evt.get("screenshot"), str):
                _track_screenshot_path(str(evt.get("screenshot")))

            stream_logs.append({
                "time": datetime.utcnow().isoformat(),
                "level": "error" if evt.get("type") == "bug_detected" else "info",
                "msg": _derive_progress_msg(evt),
                "type": evt.get("type"),
                "details": evt,
            })
            collection.update_one(
                {
                    "test_id": test_data["test_id"],
                    "user_id": user_id,
                    "status": {"$in": ["running", "cancel_requested"]},
                },
                {"$set": {"stream_logs": stream_logs, "status": "running", "ai_plan": plan, "screenshot_paths": screenshot_paths}},
                upsert=True,
            )

        from backend.agent.browser_session import BrowserSessionManager

        session_manager = BrowserSessionManager(headless=True)
        try:
            await session_manager.start()
            for raw_test_case in scenario_cases:
                elapsed_overall = perf_counter() - overall_started
                remaining_overall = OVERALL_EXECUTION_TIMEOUT_SECONDS - elapsed_overall
                if remaining_overall <= 0:
                    overall_timed_out = True
                    logger.warning("Overall AI execution timeout reached for test_id=%s", test_data.get("test_id"))
                    if progress_callback:
                        await progress_callback({
                            "type": "run_status",
                            "message": "Overall AI execution timeout reached; finalizing partial results",
                            "timeout_seconds": OVERALL_EXECUTION_TIMEOUT_SECONDS,
                        })
                    _persist_partial_state(status="timed_out", failure_reason="overall_execution_timeout")
                    break

                scenario_started = perf_counter()
                dependency_guard, dependency_info = _dependency_guard_for_scenario(raw_test_case, shared_state)
                if not dependency_guard:
                    scenario_results.append(
                        _build_scenario_result(
                            [],
                            raw_test_case,
                            "failed",
                            error="Scenario skipped due to unmet dependencies",
                            failure_reason="dependency_guard_failed",
                            failure_category="DEPENDENCY",
                            root_cause="DEPENDENCY_FAILURE",
                            recovered=False,
                            dependency_guard=dependency_info,
                        )
                    )
                    stream_logs.append(
                        {
                            "time": datetime.utcnow().isoformat(),
                            "level": "error",
                            "msg": f"Skipping scenario {raw_test_case.scenario_name or raw_test_case.title} due to unmet dependencies",
                            "type": "scenario_dependency_skip",
                            "details": dependency_info,
                        }
                    )
                    _persist_partial_state(status="running")
                    continue

                translated_case, translated_logs = translate_test_case(raw_test_case)
                translation_logs.extend(translated_logs)

                for entry in translated_logs:
                    if progress_callback:
                        await progress_callback(
                            {
                                "type": "action_translation",
                                "message": f"Original Action: {entry['original_action']} -> Normalized Action: {entry['normalized_action']}",
                                "details": entry,
                            }
                        )

                scenario_label = translated_case.scenario_name or translated_case.title or translated_case.objective_name or "Scenario"
                # Heartbeat at scenario start so the watchdog can detect intra-scenario stalls.
                watchdog.heartbeat(
                    scenario_id=translated_case.scenario_id,
                    scenario_name=translated_case.scenario_name,
                )
                if progress_callback:
                    await progress_callback(
                        {
                            "type": "run_status",
                            "message": f"Executing scenario: {scenario_label}",
                            "scenario_id": translated_case.scenario_id,
                            "scenario_name": translated_case.scenario_name,
                            "objective_id": translated_case.objective_id,
                            "objective_name": translated_case.objective_name,
                            "dependency_guard": dependency_info,
                        }
                    )

                scenario_timeout_seconds = min(90, max(1, int(remaining_overall)))
                if progress_callback:
                    await progress_callback({
                        "type": "run_status",
                        "message": f"Starting scenario timer: {scenario_label}",
                        "scenario_id": translated_case.scenario_id,
                        "scenario_name": translated_case.scenario_name,
                        "timeout_seconds": scenario_timeout_seconds,
                    })
                scenario_run = await asyncio.wait_for(
                    _run_scenario_with_replanning(
                        url=url,
                        scenario_case=translated_case,
                        dom=dom,
                        discovery=test_data["discovery"],
                        progress_callback=progress_callback,
                        shared_state=shared_state,
                        session_manager=session_manager,
                    ),
                    timeout=scenario_timeout_seconds,
                )
                scenario_runtime_ms = round((perf_counter() - scenario_started) * 1000, 1)
                step_results = scenario_run.get("step_results", [])
                failure_context = scenario_run.get("failure_context", {})
                scenario_run_status = str((scenario_run.get("result", {}) or {}).get("run_status") or "").lower()
                scenario_failed = any(item.get("status") == "fail" for item in step_results) or scenario_run_status in {"failed", "timed_out", "timeout", "cancelled"}
                scenario_status = "failed" if scenario_failed else "completed"
                if scenario_run_status in {"timed_out", "timeout", "cancelled"} and scenario_timeout_seconds < 90:
                    overall_timed_out = True
                shared_state = scenario_run.get("shared_state") or _update_shared_state_from_run(shared_state, translated_case, scenario_run.get("result", {}))
                scenario_results.append(
                    _build_scenario_result(
                        step_results,
                        translated_case,
                        scenario_status,
                        error=None if scenario_run.get("recovered") else failure_context.get("failure_reason"),
                        failure_reason=failure_context.get("failure_reason"),
                        failure_category=failure_context.get("failure_category"),
                        root_cause=failure_context.get("root_cause"),
                        recovery_strategy=scenario_run.get("recovery_strategy"),
                        recovery_attempts=scenario_run.get("recovery_attempts", 0),
                        recovery_history=scenario_run.get("recovery_history"),
                        recovered=bool(scenario_run.get("recovered")),
                        dependency_guard=dependency_info,
                        runtime_ms=scenario_runtime_ms,
                    )
                )
                _persist_partial_state(status="running")
        finally:
            try:
                await session_manager.shutdown()
            except Exception:
                logger.exception("BrowserSessionManager shutdown failed during AI execution finalization")
            finally:
                if watchdog_timer is not None:
                    watchdog_timer.stop()

        objective_coverage = _build_objective_coverage(plan.get("objective_tracking") or [], scenario_results)
        risk_summary = (plan.get("plan_metrics") or {}).get("risk_summary") if isinstance(plan.get("plan_metrics"), dict) else {}

        test_data["results"] = scenario_results
        if overall_timed_out:
            test_data["status"] = "timed_out"
            test_data["failure_reason"] = test_data.get("failure_reason") or "overall_execution_timeout"
        else:
            test_data["status"] = "completed_with_failures" if any(item.get("status") == "fail" for item in scenario_results) else "completed"
        test_data["objective_coverage"] = objective_coverage
        test_data["risk_summary"] = risk_summary or {
            "critical_features": 0,
            "high_features": 0,
            "medium_features": 0,
            "low_features": 0,
            "critical_scenarios": 0,
            "high_scenarios": 0,
            "medium_scenarios": 0,
            "low_scenarios": 0,
        }
        test_data["summary"] = {
            "total": len(scenario_results),
            "passed": sum(1 for item in scenario_results if item.get("status") == "pass"),
            "failed": sum(1 for item in scenario_results if item.get("status") == "fail"),
            "info": 0,
        }

        try:
            # Truth engine is the single source of truth for scenario /
            # step / overall status. calculate_health_score is used only
            # for auxiliary diagnostic fields (coverage / confidence /
            # pass-rate) -- it can never override the canonical verdict.
            truth = _apply_truth_engine(test_data, scenario_results)
            canonical_scenarios = truth.get("scenario_results") or []
            score_data = calculate_health_score(
                canonical_scenarios,
                objective_coverage=objective_coverage,
            )
            test_data["coverage_score"] = score_data.get("coverage_score", test_data.get("health_score", 0))
            test_data["confidence_score"] = score_data.get("confidence_score", 0)
            test_data["objective_pass_rate"] = score_data.get("objective_pass_rate", 0)
            test_data["scenario_pass_rate"] = score_data.get("scenario_pass_rate", 0)
            test_data["critical_objective_failures"] = score_data.get("critical_objective_failures", 0)
        except Exception:
            test_data["health_score"] = 0

        test_data["summary"].update(_collect_recovery_summary(test_data.get("scenario_results") or scenario_results))
        failure_category_counts = collect_failure_category_counts(test_data.get("scenario_results") or scenario_results)
        insights = test_data.get("insights") or {}
        test_data["recommendations"] = generate_recommendations(insights)
        test_data["report"] = generate_report(test_data.get("health_score", 0), test_data.get("summary"), insights)
        test_data["ai_summary"] = generate_summary_line(test_data.get("health_score", 0), test_data.get("summary"), insights, dict(failure_category_counts))
        if objective_coverage:
            objective_summary_line = ", ".join(
                f"{item['objective_name']}: {item['execution_status']}" for item in objective_coverage
            )
            test_data["ai_summary"] = f"{test_data['ai_summary']} Objective coverage -> {objective_summary_line}."

        # ---- Emit explicit terminal completion event ----
        total_duration_s = round(perf_counter() - overall_started, 2)
        final_status = test_data["status"]
        summary = test_data.get("summary", {})
        total_scenarios = summary.get("total", len(scenario_results))
        passed_scenarios = summary.get("passed", 0)
        failed_scenarios = summary.get("failed", 0)
        screenshots_captured = len(screenshot_paths)

        if final_status == "completed":
            terminal_label = "[SUCCESS] Test execution completed"
            terminal_level = "info"
        elif final_status == "timed_out":
            terminal_label = "[ERROR] Test execution timed out"
            terminal_level = "error"
        else:
            terminal_label = "[ERROR] Test execution completed with failures"
            terminal_level = "error"

        terminal_summary_text = (
            f"{terminal_label}\n"
            f"  Total Scenarios : {total_scenarios}\n"
            f"  Passed          : {passed_scenarios}\n"
            f"  Failed          : {failed_scenarios}\n"
            f"  Screenshots     : {screenshots_captured}\n"
            f"  Duration        : {total_duration_s}s"
        )
        stream_logs.append({
            "time": datetime.utcnow().isoformat(),
            "level": terminal_level,
            "msg": terminal_summary_text,
            "type": "terminal_summary",
            "details": {
                "final_status": final_status,
                "total_scenarios": total_scenarios,
                "passed": passed_scenarios,
                "failed": failed_scenarios,
                "screenshots_captured": screenshots_captured,
                "duration_seconds": total_duration_s,
            },
        })
        test_data["stream_logs"] = stream_logs
        test_data["screenshot_paths"] = screenshot_paths
        test_data["ai_report"] = {
            "user_id": user_id,
            "execution_id": test_data["test_id"],
            "website_health_score": test_data.get("health_score", 0),
            "workflow_completion": test_data.get("overall_status"),
            "critical_issues": len(insights.get("critical", [])),
            "warnings": len(insights.get("moderate", [])) + len(insights.get("minor", [])),
            "screenshots": screenshot_paths,
            "report": test_data["report"],
            "insights": insights,
            "generated_plan": plan,
            "discovery": test_data.get("discovery") or plan.get("discovery") or {"feature_map": [], "workflows": [], "forms": [], "pages": []},
            "discovery_status": test_data.get("discovery_status"),
            "discovery_error": test_data.get("discovery_error"),
            "raw_ai_plan": plan_case,
            "normalized_ai_plan": test_data.get("normalized_ai_plan") or {},
            "plan_metrics": plan_validation_payload,
            "objective_coverage": objective_coverage,
            "scenario_tree": test_data.get("scenario_tree") or plan.get("scenario_tree") or {},
            "risk_summary": test_data.get("risk_summary"),
            "recovery_summary": _collect_recovery_summary(scenario_results),
            "run_status": test_data["status"],
        }

        # ---- GUARANTEED TERMINAL WRITE (no status guard) ----
        # 1) Write the authoritative terminal status with the full payload.
        #    This is the "source of truth" write that the frontend polls.
        # 2) Best-effort: create bugs, save report. These are allowed to fail.
        async def _create_bugs_best_effort() -> None:
            try:
                created = create_bugs_from_test(test_data)
                test_data["bugs"] = [bug["bug_id"] for bug in created]
            except Exception:
                logger.exception("create_bugs_from_test failed for test_id=%s", test_data.get("test_id"))

        async def _reconcile_bugs_best_effort() -> None:
            """Resolve previously-open bug lifecycle records that this run
            has now demonstrated to be fixed. Best-effort: failures here are
            logged but do not affect the terminal state of the run.
            """
            try:
                resolved = reconcile_bugs_on_passing_run(test_data)
                if resolved:
                    test_data["resolved_bug_lifecycle"] = [
                        record.get("fingerprint") for record in resolved
                    ]
                    logger.info(
                        "Reconciled %d bug lifecycle record(s) to Resolved for test_id=%s",
                        len(resolved),
                        test_data.get("test_id"),
                    )
            except Exception:
                logger.exception(
                    "reconcile_bugs_on_passing_run failed for test_id=%s",
                    test_data.get("test_id"),
                )
            # Mirror manually-closed bugs from the bugs collection so
            # lifecycle stays in sync (best-effort).
            try:
                synced = sync_bugs_collection_to_lifecycle()
                if synced:
                    logger.info(
                        "Synced %d manually-closed bug(s) into bug_lifecycle",
                        synced,
                    )
            except Exception:
                logger.exception("sync_bugs_collection_to_lifecycle failed for test_id=%s", test_data.get("test_id"))

        async def _save_report_best_effort() -> None:
            try:
                save_report(
                    test_data,
                    report_type="ai",
                    user_id=user_id,
                    test_run_id=test_data["test_id"],
                    title=test_data.get("project") or plan_title or test_data["test_id"],
                    summary=test_data.get("ai_summary") or test_data.get("report") or "AI execution report.",
                    status=test_data.get("status"),
                )
            except Exception:
                logger.exception("save_report failed for test_id=%s", test_data.get("test_id"))

        async def _close_browser_best_effort() -> None:
            # Session manager is already shut down in the try/finally above.
            # This is a no-op left in place for symmetry with the cancel path.
            return None

        try:
            await enforce_terminal_write(
                test_id=test_data["test_id"],
                user_id=user_id,
                payload=test_data,
                save_report_fn=_save_report_best_effort,
                create_bugs_fn=_create_bugs_best_effort,
                close_browser_fn=_close_browser_best_effort,
                reconcile_bugs_fn=_reconcile_bugs_best_effort,
            )
        except Exception:
            logger.exception("enforce_terminal_write crashed for test_id=%s; falling back to direct write", test_data.get("test_id"))
            try:
                collection.update_one(
                    {"test_id": test_data["test_id"], "user_id": user_id},
                    {"$set": test_data},
                    upsert=True,
                )
            except Exception:
                logger.exception("Fallback terminal write also failed for test_id=%s", test_data.get("test_id"))
        return test_data
    except asyncio.CancelledError:
        logger.warning("AI execution cancelled; finalizing partial results for test_id=%s", test_data.get("test_id"))
        if watchdog_timer is not None:
            watchdog_timer.stop()
        partial_results = test_data.get("results") if isinstance(test_data.get("results"), list) else []
        if not partial_results:
            partial_results = []
        test_data["status"] = "cancelled"
        test_data["failure_reason"] = test_data.get("failure_reason") or "execution_cancelled"
        test_data["results"] = partial_results

        # ---- Emit explicit terminal cancellation event ----
        cancel_duration_s = round(perf_counter() - overall_started, 2)
        cancel_passed = sum(1 for r in partial_results if isinstance(r, dict) and r.get("status") == "pass")
        cancel_failed = sum(1 for r in partial_results if isinstance(r, dict) and r.get("status") == "fail")
        cancel_summary_text = (
            f"[WARNING] Test execution cancelled\n"
            f"  Total Scenarios : {len(partial_results)}\n"
            f"  Passed          : {cancel_passed}\n"
            f"  Failed          : {cancel_failed}\n"
            f"  Duration        : {cancel_duration_s}s"
        )
        cancel_logs = test_data.get("stream_logs") if isinstance(test_data.get("stream_logs"), list) else []
        cancel_logs.append({
            "time": datetime.utcnow().isoformat(),
            "level": "warning",
            "msg": cancel_summary_text,
            "type": "terminal_summary",
            "details": {
                "final_status": "cancelled",
                "total_scenarios": len(partial_results),
                "passed": cancel_passed,
                "failed": cancel_failed,
                "duration_seconds": cancel_duration_s,
            },
        })
        test_data["stream_logs"] = cancel_logs

        async def _create_bugs_cancel() -> None:
            try:
                create_bugs_from_test(test_data)
            except Exception:
                logger.exception("Bug creation failed during cancellation for test_id=%s", test_data.get("test_id"))

        async def _reconcile_bugs_cancel() -> None:
            try:
                reconcile_bugs_on_passing_run(test_data)
            except Exception:
                logger.exception("Bug reconciliation failed during cancellation for test_id=%s", test_data.get("test_id"))

        async def _save_report_cancel() -> None:
            try:
                save_report(
                    test_data,
                    report_type="ai",
                    user_id=user_id,
                    test_run_id=test_data["test_id"],
                    title=test_data.get("project") or test_data["test_id"],
                    summary=(
                        f"Test execution cancelled. Total scenarios: {len(partial_results)}. "
                        f"Duration: {cancel_duration_s}s."
                    ),
                    status=test_data.get("status"),
                )
            except Exception:
                logger.exception("save_report failed during cancellation for test_id=%s", test_data.get("test_id"))

        try:
            await enforce_terminal_write(
                test_id=test_data["test_id"],
                user_id=user_id,
                payload=test_data,
                save_report_fn=_save_report_cancel,
                create_bugs_fn=_create_bugs_cancel,
                reconcile_bugs_fn=_reconcile_bugs_cancel,
            )
        except Exception:
            logger.exception("enforce_terminal_write failed during cancellation for test_id=%s", test_data.get("test_id"))
        return test_data
    except Exception as e:
        tb = traceback.format_exc()
        if watchdog_timer is not None:
            watchdog_timer.stop()
        is_timeout = isinstance(e, asyncio.TimeoutError) or "watchdog" in str(e).lower()
        if is_timeout:
            test_data["status"] = "timed_out"
            test_data["failure_reason"] = "scenario_or_watchdog_timeout"
        else:
            test_data["status"] = "failed"
            test_data["failure_reason"] = "execution_exception"
        test_data["results"] = [{"error": str(e), "traceback": tb}]

        # ---- Emit explicit terminal failure event ----
        error_duration_s = round(perf_counter() - overall_started, 2)
        error_summary_text = (
            f"[ERROR] Test execution failed\n"
            f"  Error           : {str(e)[:200]}\n"
            f"  Duration        : {error_duration_s}s"
        )
        error_logs = test_data.get("stream_logs") if isinstance(test_data.get("stream_logs"), list) else []
        error_logs.append({
            "time": datetime.utcnow().isoformat(),
            "level": "error",
            "msg": error_summary_text,
            "type": "terminal_summary",
            "details": {
                "final_status": "failed",
                "error": str(e),
                "duration_seconds": error_duration_s,
            },
        })
        test_data["stream_logs"] = error_logs

        async def _create_bugs_exc() -> None:
            try:
                create_bugs_from_test(test_data)
            except Exception:
                logger.exception("Bug creation failed during exception finalization for test_id=%s", test_data.get("test_id"))

        async def _save_report_exc() -> None:
            try:
                save_report(
                    test_data,
                    report_type="ai",
                    user_id=user_id,
                    test_run_id=test_data["test_id"],
                    title=test_data.get("project") or test_data["test_id"],
                    summary=f"Test execution failed. Error: {str(e)[:200]}. Duration: {error_duration_s}s.",
                    status=test_data.get("status"),
                )
            except Exception:
                logger.exception("save_report failed during exception finalization for test_id=%s", test_data.get("test_id"))

        try:
            await enforce_terminal_write(
                test_id=test_data["test_id"],
                user_id=user_id,
                payload=test_data,
                save_report_fn=_save_report_exc,
                create_bugs_fn=_create_bugs_exc,
            )
        except Exception:
            logger.exception("enforce_terminal_write failed during exception for test_id=%s", test_data.get("test_id"))
        return test_data

