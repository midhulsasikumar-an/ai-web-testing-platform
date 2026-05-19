from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi.encoders import jsonable_encoder

from backend.services.execution_analysis_service import analyze_execution
from backend.core.models.report_models import AIReadableReport
from backend.services.bug_lifecycle_service import ingest_bug_lifecycle, summarize_bug_lifecycle
from backend.services.report_llm_service import enhance_narrative
from backend.database.report_repository import save_report
from backend.database.mongo import db

logger = logging.getLogger("services.ai_report")


def generate_report(run_data: Dict[str, Any], use_llm: bool = True) -> Dict[str, Any]:
    """Generate an AI-readable report from raw autonomous agent run data.

    This function is deterministic and will gracefully fall back if LLMs are not available.
    """
    try:
        analysis = analyze_execution(run_data)
        summary = analysis["summary"]
        workflow = analysis["workflow"]
        timeline = analysis["timeline"]
        issues = analysis["issues"]
        executive_summary = analysis.get("executive_summary", "")
        overall_health_assessment = analysis.get("overall_health_assessment", {})
        workflow_analysis = analysis.get("workflow_analysis", {})
        authentication_analysis = analysis.get("authentication_analysis", {})
        detected_bugs = analysis.get("detected_bugs", [])
        visual_findings = analysis.get("visual_findings", [])
        network_findings = analysis.get("network_findings", [])
        console_errors = analysis.get("console_errors", [])
        workflow_failures = analysis.get("workflow_failures", [])
        risk_assessment = analysis.get("risk_assessment", {})
        business_impact = analysis.get("business_impact", [])
        recommendations = analysis.get("recommendations", [])
        coverage_summary = analysis.get("coverage_summary", {})
        accessibility_findings = analysis.get("accessibility_findings", [])
        performance_findings = analysis.get("performance_findings", [])
        performance_summary = analysis.get("performance_summary", {})
        bug_clusters = analysis.get("bug_clusters", [])
        timeline_events = analysis.get("timeline_events", [])
        semantic_navigation_summary = analysis.get("semantic_navigation_summary", "")
        completed_goals = analysis.get("completed_goals", [])
        failed_goals = analysis.get("failed_goals", [])
        detected_modules = analysis.get("detected_modules", [])
        user_journey = analysis.get("user_journey", [])
        completed_modules = analysis.get("completed_modules", [])
        locked_routes = analysis.get("locked_routes", [])
        authentication_strategy = analysis.get("authentication_strategy", "")
        authentication_result = analysis.get("authentication_result", "")
        authentication_confidence = analysis.get("authentication_confidence", 0.0)
        authentication_reasoning = analysis.get("authentication_reasoning", [])
        severity_breakdown = analysis.get("severity_breakdown", {})
        coverage_summary = analysis.get("coverage_summary", {})
        repeated_action_prevention_summary = analysis.get("repeated_action_prevention_summary", {})
        visual_bug_summary = analysis.get("visual_bug_summary", [])
        workflow_stability_summary = analysis.get("workflow_stability_summary", {})
        success_scoring = analysis.get("success_scoring", {})

        base_narrative = _build_narrative(
            run_data,
            summary,
            workflow,
            issues,
            semantic_navigation_summary=semantic_navigation_summary,
            completed_goals=completed_goals,
            failed_goals=failed_goals,
            detected_modules=detected_modules,
            user_journey=user_journey,
            executive_summary=executive_summary,
            workflow_analysis=workflow_analysis,
            authentication_analysis=authentication_analysis,
            coverage_summary=coverage_summary,
            completed_modules=completed_modules,
            locked_routes=locked_routes,
            repeated_action_prevention_summary=repeated_action_prevention_summary,
            visual_bug_summary=visual_bug_summary,
            workflow_stability_summary=workflow_stability_summary,
            success_scoring=success_scoring,
        )

        enhanced = None
        if use_llm:
            prompt = _llm_prompt(run_data, base_narrative)
            enhanced = enhance_narrative(prompt)

        narrative = enhanced or base_narrative
        screenshots = _collect_screenshots(run_data)
        execution_summary = {
            "pages_visited": summary.pages_visited,
            "actions_executed": summary.actions_executed,
            "recoveries_triggered": summary.recoveries_triggered,
            "duration_seconds": summary.duration_seconds,
            "success_rate": summary.success_rate,
            "workflow_completion": workflow_analysis.get("workflow_completion", 0.0),
            "semantic_navigation_summary": semantic_navigation_summary,
        }

        ai_report = {
            "executive_summary": executive_summary,
            "overall_health_assessment": overall_health_assessment,
            "workflow_analysis": workflow_analysis,
            "authentication_analysis": authentication_analysis,
            "detected_bugs": detected_bugs,
            "visual_findings": visual_findings,
            "network_findings": network_findings,
            "console_errors": console_errors,
            "workflow_failures": workflow_failures,
            "accessibility_findings": accessibility_findings,
            "performance_findings": performance_findings,
            "performance_summary": performance_summary,
            "bug_clusters": bug_clusters,
            "timeline_events": timeline_events,
            "risk_assessment": risk_assessment,
            "business_impact": business_impact,
            "recommendations": recommendations,
            "coverage_summary": coverage_summary,
            "coverage": coverage_summary,
            "semantic_navigation_summary": semantic_navigation_summary,
            "completed_modules": completed_modules,
            "locked_routes": locked_routes,
            "repeated_action_prevention_summary": repeated_action_prevention_summary,
            "visual_bug_summary": visual_bug_summary,
            "workflow_stability_summary": workflow_stability_summary,
            "success_scoring": success_scoring,
            "authentication_summary": _build_authentication_summary(run_data, authentication_strategy, authentication_result, authentication_confidence),
            "interaction_narrative": narrative,
            "execution_timeline": timeline,
            "screenshots": screenshots,
            "severity_breakdown": severity_breakdown,
            "report_core": AIReadableReport(
                run_id=run_data.get("run_id", ""),
                status=run_data.get("status", ""),
                goal=run_data.get("goal"),
                summary=summary,
                workflow=workflow,
                narrative=narrative,
                authentication_strategy=authentication_strategy,
                authentication_result=authentication_result,
                authentication_confidence=authentication_confidence,
                authentication_reasoning=authentication_reasoning,
                semantic_navigation_summary=semantic_navigation_summary,
                completed_goals=completed_goals,
                failed_goals=failed_goals,
                detected_modules=detected_modules,
                user_journey=user_journey,
                interaction_narrative=base_narrative,
                issues=issues,
                failure_analysis=analysis.get("failure_analysis"),
                screenshots=screenshots,
                recommendations=[],
            ).model_dump(mode="json"),
        }

        status = run_data.get("status", "")
        critical_issues = sum(1 for bug in detected_bugs if bug.get("severity") == "critical")
        high_issues = sum(1 for bug in detected_bugs if bug.get("severity") == "high")
        medium_issues = sum(1 for bug in detected_bugs if bug.get("severity") == "medium")
        low_issues = sum(1 for bug in detected_bugs if bug.get("severity") == "low")
        website_health_score = int(max(0, min(100, overall_health_assessment.get("health_score", 0))))
        workflow_completion = float(workflow_analysis.get("workflow_completion", 0.0))

        final_report = {
            "status": status,
            "website_health_score": website_health_score,
            "workflow_completion": workflow_completion,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "medium_issues": medium_issues,
            "low_issues": low_issues,
            "ai_report": ai_report,
            "screenshots": screenshots,
            "coverage": coverage_summary,
            "execution_summary": execution_summary,
            "debug_data": run_data,
            "summary": summary.model_dump(mode="json"),
            "report_sections": {
                "executive_summary": executive_summary,
                "overall_health_assessment": overall_health_assessment,
                "workflow_analysis": workflow_analysis,
                "authentication_analysis": authentication_analysis,
                "detected_bugs": detected_bugs,
                "visual_findings": visual_findings,
                "network_findings": network_findings,
                "console_errors": console_errors,
                "workflow_failures": workflow_failures,
                "accessibility_findings": accessibility_findings,
                "performance_findings": performance_findings,
                "performance_summary": performance_summary,
                "bug_clusters": bug_clusters,
                "timeline_events": timeline_events,
                "risk_assessment": risk_assessment,
                "business_impact": business_impact,
                "recommendations": recommendations,
                "coverage_summary": coverage_summary,
                "completed_modules": completed_modules,
                "locked_routes": locked_routes,
                "repeated_action_prevention_summary": repeated_action_prevention_summary,
                "visual_bug_summary": visual_bug_summary,
                "workflow_stability_summary": workflow_stability_summary,
                "success_scoring": success_scoring,
            },
        }

        saved_id = save_report(jsonable_encoder(final_report))
        final_report["report_id"] = saved_id
        try:
            lifecycle_records = ingest_bug_lifecycle(run_data, final_report)
            final_report["bug_lifecycle"] = {
                "summary": summarize_bug_lifecycle(),
                "ingested": len(lifecycle_records),
                "records": lifecycle_records,
            }
            db["reports"].update_one({"report_id": saved_id}, {"$set": {"bug_lifecycle": final_report["bug_lifecycle"]}})
        except Exception:
            logger.exception("bug lifecycle ingestion failed", extra={"report_id": saved_id, "run_id": run_data.get("run_id")})
        logger.info("report persisted", extra={"report_id": saved_id, "run_id": run_data.get("run_id")})
        return final_report
    except Exception as e:
        logger.exception("report generation failed: %s", e)
        # Fallback minimal report
        fallback = {
            "status": run_data.get("status"),
            "website_health_score": 0,
            "workflow_completion": 0.0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
            "ai_report": {
                "executive_summary": "Report generation failed; returning raw execution summary.",
                "recommendations": [],
                "coverage_summary": {},
            },
            "screenshots": [],
            "coverage": {},
            "execution_summary": {"pages_visited": len(run_data.get("steps", []))},
            "debug_data": run_data,
        }
        try:
            save_report(jsonable_encoder(fallback))
        except Exception:
            logger.exception("failed to persist fallback report")
        return fallback


def _build_narrative(
    run_data: Dict[str, Any],
    summary: Any,
    workflow: Any,
    issues: Any,
    *,
    semantic_navigation_summary: str = "",
    completed_goals: list[str] | None = None,
    failed_goals: list[str] | None = None,
    detected_modules: list[str] | None = None,
    user_journey: list[str] | None = None,
    authentication_strategy: str = "",
    authentication_result: str = "",
    authentication_confidence: float = 0.0,
    authentication_reasoning: list[str] | None = None,
    executive_summary: str = "",
    workflow_analysis: Dict[str, Any] | None = None,
    authentication_analysis: Dict[str, Any] | None = None,
    coverage_summary: Dict[str, Any] | None = None,
    completed_modules: list[dict] | None = None,
    locked_routes: list[str] | None = None,
    repeated_action_prevention_summary: Dict[str, Any] | None = None,
    visual_bug_summary: list[dict] | None = None,
    workflow_stability_summary: Dict[str, Any] | None = None,
    success_scoring: Dict[str, Any] | None = None,
) -> str:
    parts = []
    if executive_summary:
        parts.append(executive_summary)
    if run_data.get("status") in {"completed", "max_steps_reached"}:
        parts.append("The autonomous agent completed the assigned task.")
    else:
        parts.append("The autonomous agent did not fully complete the task.")

    parts.append(f"It visited {summary.pages_visited} pages and executed {summary.actions_executed} actions.")
    if semantic_navigation_summary:
        parts.append(semantic_navigation_summary)
    if authentication_strategy:
        auth_line = f"Authentication strategy: {authentication_strategy}"
        if authentication_result:
            auth_line += f" ({authentication_result})"
        if authentication_confidence:
            auth_line += f" at confidence {authentication_confidence:.2f}"
        parts.append(auth_line + ".")
    if authentication_reasoning:
        parts.append("Auth reasoning: " + "; ".join(authentication_reasoning[:4]) + ".")
    if completed_goals:
        parts.append(f"Completed goals: {', '.join(completed_goals)}.")
    if failed_goals:
        parts.append(f"Failed goals: {', '.join(failed_goals)}.")
    if detected_modules:
        parts.append(f"Detected modules: {', '.join(dict.fromkeys(detected_modules))}.")
    if user_journey:
        parts.append(f"User journey: {' -> '.join(user_journey[:8])}.")
    if workflow_analysis:
        parts.append(f"Workflow analysis found {workflow_analysis.get('failure_clusters', 0)} grouped failure cluster(s).")
    if authentication_analysis:
        parts.append(
            "Authentication analysis: "
            + ("login tested; " if authentication_analysis.get("login_tested") else "login not fully tested; ")
            + ("signup tested; " if authentication_analysis.get("signup_tested") else "signup not fully tested; ")
            + ("session validated." if authentication_analysis.get("session_validated") else "session not validated.")
        )
    if coverage_summary:
        parts.append(
            f"Coverage reached {coverage_summary.get('coverage_score', 0):.0f}/100 with exploration depth {coverage_summary.get('exploration_depth', 0)}."
        )
    if completed_modules:
        module_names = [str(item.get("module", "")).replace("_", " ") for item in completed_modules if item.get("module")]
        if module_names:
            parts.append(f"Completed modules: {', '.join(dict.fromkeys(module_names[:6]))}.")
    if locked_routes:
        parts.append(f"Locked routes: {', '.join(str(route) for route in locked_routes[:4] if route)}.")
    if repeated_action_prevention_summary:
        if repeated_action_prevention_summary.get("locked_route_blocks"):
            parts.append("Repeated navigation was prevented once routes were confirmed complete.")
    if visual_bug_summary:
        parts.append(f"Visual review flagged {len(visual_bug_summary)} layout issue(s).")
    if workflow_stability_summary and workflow_stability_summary.get("stable") is not None:
        parts.append("Workflow stability was confirmed before and after key interactions." if workflow_stability_summary.get("stable") else "Workflow stability required extra waiting before state transitions.")
    if success_scoring:
        parts.append(
            f"Final success score: {success_scoring.get('overall_score', 0):.2f} ({success_scoring.get('confidence', 'low')} confidence)."
        )
    if issues:
        parts.append(f"Detected {len(issues)} issues during execution, including {', '.join({i.issue_type for i in issues})}.")
    else:
        parts.append("No significant issues were detected.")

    if workflow and workflow.completed:
        parts.append(f"Workflow concluded in state {workflow.end_state}.")

    return " ".join(parts)


def _llm_prompt(run_data: Dict[str, Any], base_narrative: str) -> str:
    return (
        "Convert the following deterministic test-run summary into a concise professional AI-agent style report:\n\n"
        + base_narrative
        + "\n\nDetails:\n"
        + str({"run_id": run_data.get("run_id"), "goal": run_data.get("goal")})
    )


def _build_authentication_summary(run_data: Dict[str, Any], strategy: str, result: str, confidence: float) -> Dict[str, Any]:
    summary = run_data.get("summary", {}) if isinstance(run_data.get("summary"), dict) else {}
    return {
        "login_tested": strategy in {"LOGIN_EXISTING_USER", "OAUTH_LOGIN"} or bool(summary.get("authenticated")),
        "signup_tested": strategy == "CREATE_NEW_ACCOUNT",
        "session_validated": bool(summary.get("authenticated")) or confidence >= 0.5,
        "account_created": strategy == "CREATE_NEW_ACCOUNT" and bool(summary.get("authenticated")),
        "authentication_success": result == "SUCCESS" or bool(summary.get("authenticated")),
    }


def _collect_screenshots(run_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    shots: List[Dict[str, Any]] = []
    for s in run_data.get("steps", []):
        obs = s.get("observation") or {}
        ss = None
        if isinstance(obs.get("screenshot"), dict):
            ss = obs.get("screenshot").get("path")
        if ss:
            shots.append({
                "artifact_url": _normalize_artifact_url(ss),
                "workflow_stage": obs.get("page_type") or s.get("workflow_state_after") or "unknown",
                "why_it_matters": "Visual evidence for the observed state and any rendering anomaly.",
            })
    return shots


def _normalize_artifact_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    normalized = path.replace("\\", "/")
    if normalized.startswith("artifacts/"):
        return "/" + normalized
    if normalized.startswith("screenshots/"):
        return "/" + normalized
    return normalized
