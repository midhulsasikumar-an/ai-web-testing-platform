from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional
import logging
from urllib.parse import urlparse

from backend.core.models.report_models import (
    ExecutionSummary,
    WorkflowSummary,
    DetectedIssue,
    FailureAnalysis,
    StepNarration,
)

logger = logging.getLogger("services.execution_analysis")


def analyze_execution(run: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze raw agent run JSON and extract structured insights."""
    steps = run.get("steps", [])
    duration = (run.get("completed_at") and run.get("started_at")) and 0.0 or 0.0
    # safe numeric extraction
    try:
        duration = float(run.get("summary", {}).get("duration_seconds", 0.0) or 0.0)
    except Exception:
        duration = 0.0

    actions_executed = len([s for s in steps if s.get("action")])
    failures = [s for s in steps if s.get("result") and not s["result"].get("success")]
    recoveries = sum(1 for s in steps if s.get("recovery_actions"))
    pages_visited = len({s.get("observation", {}).get("url") for s in steps if s.get("observation")})

    success_rate = 1.0 - (len(failures) / actions_executed) if actions_executed else 0.0

    summary = ExecutionSummary(
        success_rate=round(success_rate, 3),
        pages_visited=pages_visited,
        actions_executed=actions_executed,
        recoveries_triggered=recoveries,
        duration_seconds=round(duration, 2),
    )

    workflow = WorkflowSummary(
        start_state=run.get("workflow_state", {}).get("start") if isinstance(run.get("workflow_state"), dict) else run.get("workflow_state", ""),
        end_state=run.get("workflow_state", {}).get("end") if isinstance(run.get("workflow_state"), dict) else run.get("workflow_state", ""),
        completed=run.get("status") in {"completed", "max_steps_reached"},
    )
    summary_data = run.get("summary", {}) if isinstance(run.get("summary"), dict) else {}
    semantic_navigation_summary = str(summary_data.get("semantic_navigation_summary", "")).strip()
    completed_goals = list(summary_data.get("completed_goals", []) or [])
    failed_goals = list(summary_data.get("failed_goals", []) or [])
    detected_modules = list(summary_data.get("module_traversal_history", []) or [])
    user_journey = list(summary_data.get("user_journey", []) or [])
    authentication_strategy = str(summary_data.get("authentication_strategy", ""))
    authentication_result = str(summary_data.get("authentication_result", ""))
    authentication_confidence = float(summary_data.get("authentication_confidence", 0.0) or 0.0)
    authentication_reasoning = list(summary_data.get("authentication_reasoning", []) or [])
    accessibility_findings = list(summary_data.get("accessibility_findings", []) or [])
    performance_findings = list(summary_data.get("performance_findings", []) or [])
    performance_summary = dict(summary_data.get("performance_summary", {}) or {})
    bug_clusters = list(summary_data.get("bug_clusters", []) or [])
    timeline_events = list(summary_data.get("timeline_events", []) or [])
    completed_modules = list(summary_data.get("completed_modules", []) or [])
    locked_routes = list(summary_data.get("locked_routes", []) or [])
    coverage_summary = dict(summary_data.get("coverage_summary", {}) or {})
    repeated_action_prevention_summary = dict(summary_data.get("repeated_action_prevention_summary", {}) or {})
    visual_bug_summary = list(summary_data.get("visual_bug_summary", []) or [])
    workflow_stability_summary = dict(summary_data.get("workflow_stability_summary", {}) or {})
    success_scoring = dict(summary_data.get("success_scoring", {}) or {})

    # failure analysis
    failure_types = {}
    repeated = 0
    for s in failures:
        ft = s["result"].get("failure_type", "unknown")
        failure_types[ft] = failure_types.get(ft, 0) + 1
    repeated = sum(1 for v in failure_types.values() if v > 1)
    top = sorted([{"type": k, "count": v} for k, v in failure_types.items()], key=lambda x: -x["count"])[:5]

    failure_analysis = FailureAnalysis(
        total_failures=len(failures),
        repeated_failures=repeated,
        top_failure_types=top,
    )

    grouped_failures = _group_failures(steps)
    console_findings = _collect_console_findings(steps)
    network_findings = _collect_network_findings(steps)
    visual_findings = _collect_visual_findings(steps)
    bug_cards = _build_bug_cards(grouped_failures, console_findings, network_findings, visual_findings, steps)
    authentication_analysis = _build_authentication_analysis(run, steps, bug_cards)
    base_coverage_summary = _build_coverage_summary(run, steps)
    if coverage_summary:
        base_coverage_summary.update(coverage_summary)
    coverage_summary = base_coverage_summary
    workflow_analysis = _build_workflow_analysis(run, steps, grouped_failures)
    business_impact = _build_business_impact(bug_cards, workflow_analysis, authentication_analysis)
    recommendations = _build_recommendations(bug_cards, coverage_summary, workflow_analysis)
    risk_assessment = _build_risk_assessment(bug_cards, network_findings, authentication_analysis)
    severity_breakdown = Counter(card["severity"] for card in bug_cards)
    screenshot_intelligence = _build_screenshot_intelligence(steps, bug_cards)
    overall_health_assessment = _build_overall_health_assessment(summary, bug_cards, coverage_summary, authentication_analysis)
    executive_summary = _build_executive_summary(run, summary, bug_cards, workflow_analysis, authentication_analysis, coverage_summary)

    workflow_failures = [
        {
            "workflow_stage": card.get("workflow_stage"),
            "bug_type": card.get("bug_type"),
            "severity": card.get("severity"),
            "root_cause": card.get("root_cause"),
            "affected_area": card.get("affected_component"),
        }
        for card in bug_cards
    ]

    visual_issue_cards = [
        {
            "what": item.get("description"),
            "where": item.get("workflow_stage"),
            "impact": item.get("impact"),
            "evidence": item.get("evidence"),
        }
        for item in visual_findings
    ]

    coverage_summary["coverage_score"] = round(
        min(
            100.0,
            35.0
            + len({card.get("workflow_stage") for card in bug_cards if card.get("workflow_stage")}) * 5.0
            + min(30.0, pages_visited * 2.5)
            + min(20.0, len({step.get("observation", {}).get("page_type") for step in steps if step.get("observation")}) * 3.0)
            + (10.0 if run.get("summary", {}).get("authenticated") else 0.0),
        ),
        2,
    )
    coverage_summary["confidence_score"] = round(min(0.99, 0.45 + coverage_summary.get("exploration_depth", 0) / 20.0), 2)

    # timeline
    timeline: List[StepNarration] = []
    for idx, s in enumerate(steps):
        action = (s.get("action") or {}).get("action") if isinstance(s.get("action"), dict) else (s.get("action", {}).get("action") if isinstance(s.get("action"), dict) else s.get("action") )
        action_name = action if isinstance(action, str) else (action.get("value") if isinstance(action, dict) else str(action))
        desc = ""
        status = "success"
        result = s.get("result")
        if result:
            status = "success" if result.get("success") else "failure"
            desc = result.get("error") or result.get("recovery_hint") or ""
        obs = s.get("observation") or {}
        screenshot = obs.get("screenshot", {}).get("path") if isinstance(obs.get("screenshot"), dict) else None
        nav = s.get("navigation_transition") or {}
        semantic_desc = nav.get("summary") if isinstance(nav, dict) else None
        if semantic_desc and not desc:
            desc = semantic_desc
        elif nav.get("navigation_type") and nav.get("to_state"):
            desc = desc or f"Moved via {nav.get('navigation_type')} into {nav.get('to_state').replace('_', ' ')}"
        elif action_name and not desc:
            desc = _describe_action(action_name, s.get("action") or {}, obs)
        timeline.append(
            StepNarration(
                step=idx,
                action=str(action_name or "unknown"),
                description=str(desc or s.get("observation", {}).get("title", "")),
                status=status,
                duration_seconds=None,
                screenshot=screenshot,
            )
        )

    # issues detection
    issues = _collect_issues(steps)

    logger.info("execution analysis complete", extra={"run_id": run.get("run_id")})

    analysis_payload = {
        "summary": summary,
        "workflow": workflow,
        "failure_analysis": failure_analysis,
        "timeline": timeline,
        "issues": issues,
        "semantic_navigation_summary": semantic_navigation_summary,
        "completed_goals": completed_goals,
        "failed_goals": failed_goals,
        "detected_modules": detected_modules,
        "user_journey": user_journey,
        "authentication_strategy": authentication_strategy,
        "authentication_result": authentication_result,
        "authentication_confidence": authentication_confidence,
        "authentication_reasoning": authentication_reasoning,
        "executive_summary": executive_summary,
        "overall_health_assessment": overall_health_assessment,
        "workflow_analysis": workflow_analysis,
        "authentication_analysis": authentication_analysis,
        "detected_bugs": bug_cards,
        "visual_findings": visual_issue_cards,
        "network_findings": network_findings,
        "console_errors": console_findings,
        "workflow_failures": workflow_failures,
        "risk_assessment": risk_assessment,
        "business_impact": business_impact,
        "recommendations": recommendations,
        "coverage_summary": coverage_summary,
        "coverage": coverage_summary,
        "screenshot_intelligence": screenshot_intelligence,
        "severity_breakdown": dict(severity_breakdown),
        "accessibility_findings": accessibility_findings,
        "performance_findings": performance_findings,
        "performance_summary": performance_summary,
        "bug_clusters": bug_clusters,
        "timeline_events": timeline_events,
        "completed_modules": completed_modules,
        "locked_routes": locked_routes,
        "coverage_summary": coverage_summary,
        "repeated_action_prevention_summary": repeated_action_prevention_summary,
        "visual_bug_summary": visual_bug_summary,
        "workflow_stability_summary": workflow_stability_summary,
        "success_scoring": success_scoring,
    }
    analysis_payload["timeline"] = timeline
    analysis_payload["issues"] = issues
    analysis_payload["raw_steps"] = steps
    return analysis_payload


def _severity_from_failure(failure_type: str) -> str:
    mapping = {
        "policy_blocked": "critical",
        "invalid_action": "high",
        "selector_not_found": "medium",
        "timeout": "medium",
        "detached": "medium",
        "navigation": "high",
        "modal_blocked": "medium",
    }
    return mapping.get(failure_type, "low")


def _collect_issues(steps: List[Dict[str, Any]]) -> List[DetectedIssue]:
    issues: List[DetectedIssue] = []
    for idx, s in enumerate(steps):
        result = s.get("result")
        if result and not result.get("success"):
            ft = result.get("failure_type") or "unknown"
            severity = _severity_from_failure(ft)
            issues.append(
                DetectedIssue(
                    step=idx,
                    issue_type=ft,
                    severity=severity,
                    description=result.get("error") or "Action failed",
                    evidence={"selector": result.get("selector_used"), "action": (s.get("action") or {}).get("action") if isinstance(s.get("action"), dict) else s.get("action")},
                )
            )
    return issues


def _group_failures(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for idx, step in enumerate(steps):
        result = step.get("result") or {}
        observation = step.get("observation") or {}
        failure_type = result.get("failure_type") or "unknown"
        workflow_stage = observation.get("page_type") or step.get("workflow_state_after") or "unknown"
        selector = result.get("selector_used") or (step.get("action") or {}).get("selector") if isinstance(step.get("action"), dict) else None
        key = _failure_group_key(failure_type, workflow_stage, selector)
        clusters[key].append({
            "step": idx,
            "failure_type": failure_type,
            "workflow_stage": workflow_stage,
            "selector": selector,
            "error": result.get("error") or result.get("recovery_hint") or "",
            "url": observation.get("url") or result.get("after_url") or result.get("before_url") or "",
        })
    grouped = []
    for key, items in sorted(clusters.items(), key=lambda item: (-len(item[1]), item[0])):
        first = items[0]
        grouped.append({
            "group_key": key,
            "count": len(items),
            "failure_type": first["failure_type"],
            "workflow_stage": first["workflow_stage"],
            "selector": first["selector"],
            "steps": [item["step"] for item in items],
            "description": _failure_group_description(first["failure_type"], first["workflow_stage"], len(items)),
            "probable_root_cause": _probable_root_cause(first["failure_type"], first["workflow_stage"], items),
            "severity": _severity_from_failure(first["failure_type"]),
        })
    return grouped


def _failure_group_key(failure_type: str, workflow_stage: str, selector: Optional[str]) -> str:
    normalized_selector = (selector or "").split()[0] if selector else ""
    return f"{failure_type}:{workflow_stage}:{normalized_selector[:32]}"


def _failure_group_description(failure_type: str, workflow_stage: str, count: int) -> str:
    return f"{count} related {failure_type} failure(s) observed during {workflow_stage}."


def _probable_root_cause(failure_type: str, workflow_stage: str, items: List[Dict[str, Any]]) -> str:
    if failure_type in {"auth_failure", "session_expired"}:
        return "Authentication state was not established or was lost before protected workflow execution."
    if failure_type == "selector_not_found":
        return "The expected interactive control was missing, hidden, or renamed in the rendered UI."
    if failure_type == "navigation":
        return "A workflow transition did not materialize after an interaction, suggesting missing redirect or state handling."
    if failure_type == "modal_blocked":
        return "A modal or overlay likely blocked interaction with the target element."
    if any("console" in (item.get("error") or "").lower() for item in items):
        return "The frontend logged runtime errors that likely interrupted the expected flow."
    return f"The application failed to advance from {workflow_stage}."


def _collect_console_findings(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for idx, step in enumerate(steps):
        observation = step.get("observation") or {}
        for error in observation.get("console_errors", []) or []:
            findings.append({
                "step": idx,
                "message": error,
                "severity": "high" if any(term in error.lower() for term in ["error", "exception", "uncaught", "failed"]) else "medium",
                "workflow_stage": observation.get("page_type") or step.get("workflow_state_after") or "unknown",
                "impact": "Console error may indicate a frontend render or script failure.",
            })
    return _dedupe_dicts(findings, ["message", "workflow_stage"])


def _collect_network_findings(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for idx, step in enumerate(steps):
        observation = step.get("observation") or {}
        for failure in observation.get("network_failures", []) or []:
            findings.append({
                "step": idx,
                "message": failure,
                "severity": "critical" if any(term in failure.lower() for term in ["401", "403", "500", "timeout", "failed to fetch", "network error"]) else "high",
                "workflow_stage": observation.get("page_type") or step.get("workflow_state_after") or "unknown",
                "impact": "Network failure can prevent page data from loading or keep the workflow blocked.",
            })
    return _dedupe_dicts(findings, ["message", "workflow_stage"])


def _collect_visual_findings(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for idx, step in enumerate(steps):
        observation = step.get("observation") or {}
        text = f"{observation.get('title', '')} {observation.get('page_text', '')}".lower()
        if observation.get("screenshot") and len(observation.get("elements", [])) == 0:
            findings.append({
                "step": idx,
                "description": "Visible page captured but no interactive elements were detected.",
                "workflow_stage": observation.get("page_type") or "unknown",
                "impact": "Users may see a blank or non-interactive screen.",
                "evidence": {"screenshot": observation.get("screenshot", {}).get("path") if isinstance(observation.get("screenshot"), dict) else None},
            })
        if any(term in text for term in ["loading", "spinner", "please wait"]) and observation.get("screenshot"):
            findings.append({
                "step": idx,
                "description": "Stuck loader or prolonged loading state detected.",
                "workflow_stage": observation.get("page_type") or "unknown",
                "impact": "Users may be blocked from completing the workflow if the page never settles.",
                "evidence": {"screenshot": observation.get("screenshot", {}).get("path") if isinstance(observation.get("screenshot"), dict) else None},
            })
    return _dedupe_dicts(findings, ["description", "workflow_stage"])


def _build_bug_cards(
    grouped_failures: List[Dict[str, Any]],
    console_findings: List[Dict[str, Any]],
    network_findings: List[Dict[str, Any]],
    visual_findings: List[Dict[str, Any]],
    steps: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    bug_cards: List[Dict[str, Any]] = []
    for group in grouped_failures:
        workflow_stage = group.get("workflow_stage", "unknown")
        bug_type = _bug_type_from_failure(group.get("failure_type", "unknown"), workflow_stage)
        affected_component = _component_from_stage(workflow_stage)
        reproduction_steps = _reproduction_steps(group, steps)
        bug_cards.append({
            "title": _bug_title(bug_type, workflow_stage),
            "severity": _severity_from_failure(group.get("failure_type", "unknown")),
            "description": group.get("description"),
            "technical_explanation": group.get("probable_root_cause"),
            "impact": _business_impact_from_stage(workflow_stage, bug_type),
            "confidence": 0.93 if len(group.get("steps", [])) > 1 else 0.84,
            "workflow": _workflow_from_stage(workflow_stage),
            "workflow_stage": workflow_stage,
            "affected_component": affected_component,
            "bug_type": bug_type,
            "root_cause": group.get("probable_root_cause"),
            "reproduction_steps": reproduction_steps,
            "expected_behavior": _expected_behavior_from_stage(workflow_stage),
            "actual_behavior": group.get("description"),
            "screenshot_url": _best_screenshot_url(group, steps),
            "reproducible": len(group.get("steps", [])) > 1,
            "related_steps": group.get("steps", []),
        })

    for item in console_findings:
        bug_cards.append({
            "title": "Console runtime error",
            "severity": item.get("severity", "medium"),
            "description": item.get("message"),
            "technical_explanation": "Browser console reported an error while executing the workflow.",
            "impact": item.get("impact"),
            "confidence": 0.78,
            "workflow": "ui_experience",
            "workflow_stage": item.get("workflow_stage", "unknown"),
            "affected_component": "frontend_runtime",
            "bug_type": "console_error",
            "root_cause": item.get("message"),
            "reproduction_steps": [f"Open {item.get('workflow_stage')} and reproduce the console error."],
            "expected_behavior": "No uncaught console errors should appear.",
            "actual_behavior": item.get("message"),
            "screenshot_url": None,
            "reproducible": True,
            "related_steps": [item.get("step")],
        })

    for item in network_findings:
        bug_cards.append({
            "title": "Network failure",
            "severity": item.get("severity", "high"),
            "description": item.get("message"),
            "technical_explanation": "A network request failed while the agent was executing the workflow.",
            "impact": item.get("impact"),
            "confidence": 0.8,
            "workflow": "network",
            "workflow_stage": item.get("workflow_stage", "unknown"),
            "affected_component": "network_layer",
            "bug_type": "network_failure",
            "root_cause": item.get("message"),
            "reproduction_steps": [f"Trigger the workflow at {item.get('workflow_stage')} and observe the failing request."],
            "expected_behavior": "Network requests should succeed or fail gracefully.",
            "actual_behavior": item.get("message"),
            "screenshot_url": None,
            "reproducible": True,
            "related_steps": [item.get("step")],
        })

    for item in visual_findings:
        bug_cards.append({
            "title": "Visual rendering issue",
            "severity": "medium",
            "description": item.get("description"),
            "technical_explanation": "The rendered page appeared visually incomplete or non-interactive.",
            "impact": item.get("impact"),
            "confidence": 0.76,
            "workflow": "visual_qa",
            "workflow_stage": item.get("workflow_stage", "unknown"),
            "affected_component": "ui_layout",
            "bug_type": "visual_rendering_issue",
            "root_cause": item.get("description"),
            "reproduction_steps": [f"Navigate to {item.get('workflow_stage')} and inspect the page after it stabilizes."],
            "expected_behavior": "The page should display usable controls and content.",
            "actual_behavior": item.get("description"),
            "screenshot_url": _normalize_artifact_url(item.get("evidence", {}).get("screenshot")),
            "reproducible": True,
            "related_steps": [item.get("step")],
        })

    return _dedupe_bug_cards(bug_cards)


def _build_authentication_analysis(run: Dict[str, Any], steps: List[Dict[str, Any]], bug_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = run.get("summary", {}) if isinstance(run.get("summary"), dict) else {}
    auth_issues = [card for card in bug_cards if card.get("workflow") in {"authentication", "session", "signup", "login"}]
    login_tested = any("login" in str(step.get("workflow_state_after") or step.get("observation", {}).get("page_type") or "").lower() for step in steps)
    signup_tested = any("signup" in str(step.get("workflow_state_after") or step.get("observation", {}).get("page_type") or "").lower() for step in steps)
    session_validated = bool(summary.get("authenticated")) or any(card.get("bug_type") == "session_expired" for card in auth_issues)
    security_implications = []
    if any(card.get("bug_type") == "auth_bypass" for card in auth_issues):
        security_implications.append("Possible authentication bypass undermines account protection.")
    if any(card.get("bug_type") == "validation_failure" for card in auth_issues):
        security_implications.append("Validation gaps may allow weak or malformed credentials through.")
    if not security_implications and (login_tested or signup_tested):
        security_implications.append("Authentication paths were exercised without evidence of bypass; protected route enforcement appears intact when the session is valid.")
    return {
        "what_was_tested": [
            "login validation",
            "invalid login validation",
            "empty-field validation",
            "session validation",
            "logout validation",
            "signup validation",
            "protected route validation",
        ],
        "login_tested": login_tested,
        "signup_tested": signup_tested,
        "session_validated": session_validated,
        "authentication_success": bool(summary.get("authenticated")),
        "passed": [
            "Session remained authenticated" if summary.get("authenticated") else "Authentication workflow did not reach a persistent authenticated session",
        ],
        "failed": [card.get("title") for card in auth_issues][:5],
        "security_implications": security_implications,
        "redirect_behaviour": _auth_redirect_summary(steps),
    }


def _build_coverage_summary(run: Dict[str, Any], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    page_types = [step.get("observation", {}).get("page_type") for step in steps if step.get("observation")]
    unique_pages = [page for page in dict.fromkeys(page_types) if page]
    explored_modules = [page for page in unique_pages if page not in {"login_page", "signup_page", "oauth_page", "forgot_password_page"}]
    tested_workflows = [
        workflow for workflow in dict.fromkeys([
            "authentication" if any(page in {"login_page", "signup_page", "oauth_page"} for page in unique_pages) else None,
            "dashboard" if any(page and "dashboard" in page for page in unique_pages) else None,
            "forms" if any(page and "form" in page for page in unique_pages) else None,
            "navigation" if len(unique_pages) > 3 else None,
        ]) if workflow
    ]
    exploration_depth = len(unique_pages) + len({step.get("workflow_state_after") for step in steps if step.get("workflow_state_after")})
    untested_routes = [route for route in ["admin", "settings", "reports", "users"] if not any(route in (page or "") for page in unique_pages)]
    risky_areas = [
        "authentication" if not run.get("summary", {}).get("authenticated") else None,
        "network" if any(step.get("observation", {}).get("network_failures") for step in steps) else None,
        "console" if any(step.get("observation", {}).get("console_errors") for step in steps) else None,
    ]
    risky_areas = [item for item in risky_areas if item]
    return {
        "explored_modules": explored_modules,
        "tested_workflows": tested_workflows,
        "auth_coverage": 1.0 if run.get("summary", {}).get("authenticated") else 0.5,
        "validated_forms": len([step for step in steps if step.get("observation", {}).get("forms")]),
        "untested_routes": untested_routes,
        "risky_areas": risky_areas,
        "exploration_depth": exploration_depth,
        "confidence_score": round(min(0.99, 0.4 + exploration_depth / 20.0), 2),
    }


def _build_workflow_analysis(run: Dict[str, Any], steps: List[Dict[str, Any]], grouped_failures: List[Dict[str, Any]]) -> Dict[str, Any]:
    states = [step.get("workflow_state_after") or step.get("observation", {}).get("page_type") for step in steps]
    unique_states = [state for state in dict.fromkeys(states) if state]
    transitions = len([step for step in steps if step.get("navigation_transition")])
    return {
        "workflow_states": unique_states,
        "transitions_observed": transitions,
        "repeated_failures": [group for group in grouped_failures if group.get("count", 0) > 1],
        "workflow_completion": 1.0 if run.get("status") in {"completed", "max_steps_reached"} else 0.0,
        "stability": "stable" if transitions > 0 else "uncertain",
        "failure_clusters": len(grouped_failures),
    }


def _build_business_impact(bug_cards: List[Dict[str, Any]], workflow_analysis: Dict[str, Any], authentication_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    impacts = []
    for card in bug_cards[:8]:
        impacts.append({
            "severity": card.get("severity"),
            "impact": card.get("impact"),
            "workflow": card.get("workflow"),
            "workflow_stage": card.get("workflow_stage"),
        })
    if authentication_analysis.get("session_validated") and not authentication_analysis.get("authentication_success"):
        impacts.append({
            "severity": "high",
            "impact": "Session validation passed but authentication did not complete cleanly, creating risk for protected workflows.",
            "workflow": "authentication",
            "workflow_stage": "AUTHENTICATED",
        })
    if workflow_analysis.get("failure_clusters", 0) > 2:
        impacts.append({
            "severity": "medium",
            "impact": "Multiple grouped failures suggest a recurring workflow reliability problem.",
            "workflow": "workflow",
            "workflow_stage": "multiple",
        })
    return impacts


def _build_recommendations(bug_cards: List[Dict[str, Any]], coverage_summary: Dict[str, Any], workflow_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    recommendations = []
    if any(card.get("severity") == "critical" for card in bug_cards):
        recommendations.append({"title": "Fix critical workflow blockers", "detail": "Resolve authentication or navigation blockers before extending coverage.", "impact": "High"})
    if coverage_summary.get("untested_routes"):
        recommendations.append({"title": "Expand route coverage", "detail": f"Add tests for: {', '.join(coverage_summary['untested_routes'])}.", "impact": "Medium"})
    if workflow_analysis.get("failure_clusters", 0) > 0:
        recommendations.append({"title": "Stabilize repeated failures", "detail": "Address recurring failure groups to reduce noisy regressions.", "impact": "Medium"})
    if not recommendations:
        recommendations.append({"title": "Maintain coverage", "detail": "Continue monitoring stable workflows and expand exploratory depth.", "impact": "Low"})
    return recommendations


def _build_risk_assessment(bug_cards: List[Dict[str, Any]], network_findings: List[Dict[str, Any]], authentication_analysis: Dict[str, Any]) -> Dict[str, Any]:
    critical = sum(1 for card in bug_cards if card.get("severity") == "critical")
    high = sum(1 for card in bug_cards if card.get("severity") == "high")
    network_risk = any(item.get("severity") == "critical" for item in network_findings)
    auth_risk = not authentication_analysis.get("session_validated", False) and authentication_analysis.get("login_tested", False)
    score = max(0, 100 - critical * 30 - high * 15 - (10 if network_risk else 0) - (10 if auth_risk else 0))
    return {
        "risk_score": score,
        "critical_issues": critical,
        "high_issues": high,
        "network_risk": network_risk,
        "authentication_risk": auth_risk,
    }


def _build_screenshot_intelligence(steps: List[Dict[str, Any]], bug_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    screenshots = []
    for idx, step in enumerate(steps):
        observation = step.get("observation") or {}
        shot = observation.get("screenshot")
        shot_path = shot.get("path") if isinstance(shot, dict) else None
        if not shot_path:
            continue
        stage = step.get("workflow_state_after") or observation.get("page_type") or "unknown"
        related = [card for card in bug_cards if card.get("workflow_stage") == stage]
        screenshots.append({
            "step": idx,
            "artifact_url": _normalize_artifact_url(shot_path),
            "workflow_stage": stage,
            "why_it_matters": "Provides visual evidence for the workflow state and any rendering issue.",
            "evidence": [card.get("title") for card in related][:3],
            "state": stage,
        })
    return screenshots


def _build_overall_health_assessment(summary: ExecutionSummary, bug_cards: List[Dict[str, Any]], coverage_summary: Dict[str, Any], authentication_analysis: Dict[str, Any]) -> Dict[str, Any]:
    critical = sum(1 for card in bug_cards if card.get("severity") == "critical")
    high = sum(1 for card in bug_cards if card.get("severity") == "high")
    score = int(max(0, min(100, 100 * summary.success_rate - critical * 22 - high * 10 + (10 if authentication_analysis.get("session_validated") else 0))))
    return {
        "health_score": score,
        "status": "healthy" if score >= 80 else "degraded" if score >= 55 else "critical",
        "confidence": coverage_summary.get("confidence_score", 0.5),
    }


def _build_executive_summary(
    run: Dict[str, Any],
    summary: ExecutionSummary,
    bug_cards: List[Dict[str, Any]],
    workflow_analysis: Dict[str, Any],
    authentication_analysis: Dict[str, Any],
    coverage_summary: Dict[str, Any],
) -> str:
    status = run.get("status", "unknown")
    message = [
        f"The agent run finished with status {status} after visiting {summary.pages_visited} pages and executing {summary.actions_executed} actions.",
        f"The analysis grouped {len(bug_cards)} issue cards across {workflow_analysis.get('failure_clusters', 0)} failure clusters.",
    ]
    if authentication_analysis.get("authentication_success"):
        message.append("Authentication was validated and protected workflows were reachable.")
    elif authentication_analysis.get("login_tested"):
        message.append("Authentication was tested, but the session did not fully stabilize or reach a persistent protected state.")
    if coverage_summary.get("coverage_score", 0) >= 80:
        message.append("Coverage is broad enough to support a credible regression assessment.")
    else:
        message.append("Coverage remains partial and should be expanded for stronger confidence.")
    return " ".join(message)


def _collect_visual_findings(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for idx, step in enumerate(steps):
        observation = step.get("observation") or {}
        text = f"{observation.get('title', '')} {observation.get('page_text', '')}".lower()
        if observation.get("screenshot") and len(observation.get("elements", [])) == 0:
            findings.append({
                "step": idx,
                "description": "Visible page captured but no interactive elements were detected.",
                "workflow_stage": observation.get("page_type") or "unknown",
                "impact": "Users may see a blank or non-interactive screen.",
                "evidence": {"screenshot": observation.get("screenshot", {}).get("path") if isinstance(observation.get("screenshot"), dict) else None},
            })
        if any(term in text for term in ["loading", "spinner", "please wait"]) and observation.get("screenshot"):
            findings.append({
                "step": idx,
                "description": "Stuck loader or prolonged loading state detected.",
                "workflow_stage": observation.get("page_type") or "unknown",
                "impact": "Users may be blocked from completing the workflow if the page never settles.",
                "evidence": {"screenshot": observation.get("screenshot", {}).get("path") if isinstance(observation.get("screenshot"), dict) else None},
            })
    return _dedupe_dicts(findings, ["description", "workflow_stage"])


def _dedupe_dicts(items: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    seen = set()
    output = []
    for item in items:
        marker = tuple(item.get(key) for key in keys)
        if marker in seen:
            continue
        seen.add(marker)
        output.append(item)
    return output


def _dedupe_bug_cards(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []
    for item in items:
        marker = (item.get("bug_type"), item.get("workflow_stage"), item.get("description"))
        if marker in seen:
            continue
        seen.add(marker)
        output.append(item)
    return output


def _normalize_artifact_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    normalized = path.replace("\\", "/")
    if normalized.startswith("artifacts/"):
        return "/" + normalized
    if normalized.startswith("screenshots/"):
        return "/" + normalized
    return normalized


def _best_screenshot_url(group: Dict[str, Any], steps: List[Dict[str, Any]]) -> Optional[str]:
    for step_index in group.get("steps", [])[:1]:
        observation = steps[step_index].get("observation") or {}
        shot = observation.get("screenshot")
        if isinstance(shot, dict) and shot.get("path"):
            return _normalize_artifact_url(shot.get("path"))
    return None


def _reproduction_steps(group: Dict[str, Any], steps: List[Dict[str, Any]]) -> List[str]:
    result = []
    for step_index in group.get("steps", [])[:5]:
        step = steps[step_index]
        action = step.get("action") or {}
        if isinstance(action, dict):
            action_name = action.get("action") or "action"
            target = action.get("target") or action.get("selector") or action.get("value") or ""
        else:
            action_name = str(action)
            target = ""
        stage = step.get("workflow_state_after") or step.get("observation", {}).get("page_type") or "unknown"
        result.append(f"{action_name} {target} at {stage}".strip())
    return result or ["Reproduce by following the observed workflow until the failure reappears."]


def _workflow_from_stage(workflow_stage: str) -> str:
    if "login" in workflow_stage or "signup" in workflow_stage or "oauth" in workflow_stage or "forgot" in workflow_stage:
        return "authentication"
    if "dashboard" in workflow_stage or "admin" in workflow_stage or "settings" in workflow_stage:
        return "navigation"
    if "form" in workflow_stage:
        return "forms"
    return "exploration"


def _bug_type_from_failure(failure_type: str, workflow_stage: str) -> str:
    if failure_type in {"auth_failure", "session_expired"}:
        return "authentication_validation_failure"
    if failure_type == "selector_not_found":
        return "missing_ui_component"
    if failure_type == "navigation":
        return "navigation_failure"
    if failure_type == "modal_blocked":
        return "overlay_blocking_interaction"
    if failure_type == "network_error":
        return "network_failure"
    if failure_type == "timeout":
        return "stuck_loader_or_timeout"
    if "dashboard" in workflow_stage and failure_type == "invalid_action":
        return "dashboard_access_failure"
    return f"{failure_type}_failure"


def _component_from_stage(workflow_stage: str) -> str:
    if any(term in workflow_stage for term in ["login", "signup", "oauth", "forgot"]):
        return "authentication"
    if "dashboard" in workflow_stage or "admin" in workflow_stage or "navigation" in workflow_stage:
        return "navigation"
    if "form" in workflow_stage:
        return "forms"
    return "ui"


def _bug_title(bug_type: str, workflow_stage: str) -> str:
    pretty = bug_type.replace("_", " ").title()
    return f"{pretty} in {workflow_stage.replace('_', ' ').title()}" if workflow_stage else pretty


def _expected_behavior_from_stage(workflow_stage: str) -> str:
    if "login" in workflow_stage:
        return "Login submission should validate credentials and redirect to an authenticated dashboard."
    if "signup" in workflow_stage:
        return "Signup workflow should validate inputs and, when allowed, create an account."
    if "dashboard" in workflow_stage:
        return "Protected dashboard content should render and remain accessible."
    return "The workflow should continue to the next semantic state without blocking errors."


def _business_impact_from_stage(workflow_stage: str, bug_type: str) -> str:
    if bug_type.startswith("authentication"):
        return "Users cannot reliably sign in or validate account access."
    if bug_type.startswith("navigation"):
        return "Users cannot reach the expected destination or protected area."
    if bug_type.startswith("network"):
        return "The page may fail to load data or complete server-backed actions."
    if bug_type.startswith("visual"):
        return "Users may be blocked by a broken or unreadable interface."
    return f"The issue interrupts the expected experience at {workflow_stage}."


def _auth_redirect_summary(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    redirects = []
    for idx, step in enumerate(steps):
        nav = step.get("navigation_transition") or {}
        if nav.get("url_before") and nav.get("url_after") and nav.get("url_before") != nav.get("url_after"):
            redirects.append({
                "step": idx,
                "from": nav.get("url_before"),
                "to": nav.get("url_after"),
                "workflow_stage": nav.get("to_state") or step.get("workflow_state_after") or "unknown",
            })
    return redirects[-8:]


def _describe_action(action_name: str, action_data: Dict[str, Any], observation: Dict[str, Any]) -> str:
    target = action_data.get("target") or action_data.get("selector") or action_data.get("url") or action_data.get("value")
    page_type = observation.get("page_type") or observation.get("title") or "page"
    verb = action_name.lower()
    if verb == "click":
        return f"Clicked {target or 'interactive control'} on {page_type}."
    if verb == "fill":
        return f"Filled {target or 'form field'} on {page_type}."
    if verb == "select":
        return f"Selected {target or 'option'} on {page_type}."
    if verb == "navigate":
        return f"Navigated to {target or 'target location'} from {page_type}."
    if verb == "wait":
        return f"Waited for the interface to stabilize on {page_type}."
    return f"Executed {action_name} on {page_type}."
