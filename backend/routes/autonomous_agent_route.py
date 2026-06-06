from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from backend.agent.agent_loop_v2 import run_agent_loop_v2
from backend.agent.browser_session import BrowserSessionManager
from backend.core.models.agent_state import AgentRunRequest
from backend.models.schema import TestRequest
from backend.services.ai_plan_service import generate_autonomous_qa_plan
from backend.services.ai_report_service import generate_report
from backend.agent.services.stability_service import StabilityService
from backend.services.auth import get_current_user
from backend.services.test_services import create_test_run, run_ai_plan_and_update

router = APIRouter()


@router.post("/autonomous-test")
async def autonomous_test(data: AgentRunRequest, current_user: dict = Depends(get_current_user)):
    start_url = str(data.url)

    if not data.goal or not str(data.goal).strip():
        plan = await generate_autonomous_qa_plan(start_url)
        request = TestRequest(
            url=start_url,
            test_name="Autonomous QA",
            goal=plan.get("instruction"),
            project_name="Autonomous QA",
            test_type="autonomous_qa",
            ai_plan=plan,
        )
        test_data = create_test_run(request, current_user["user_id"])
        run_data = await run_ai_plan_and_update(test_data, start_url, current_user["user_id"], plan)
        discovery = run_data.get("discovery") or plan.get("discovery") or {}
        objective_coverage = list(run_data.get("objective_coverage", []) or [])
        test_coverage = {
            "objective_pass_rate": run_data.get("objective_pass_rate", 0),
            "scenario_pass_rate": run_data.get("scenario_pass_rate", 0),
            "critical_objective_failures": run_data.get("critical_objective_failures", 0),
            "coverage_score": run_data.get("coverage_score", run_data.get("health_score", 0)),
            "health_score": run_data.get("health_score", 0),
            "confidence_score": run_data.get("confidence_score", 0),
        }

        return {
            "success": run_data.get("status") in {"completed", "completed_with_failures", "max_steps_reached"},
            "mode": "autonomous_qa",
            "status": run_data.get("status"),
            "discovered_features": discovery.get("feature_map", []),
            "discovered_workflows": discovery.get("workflows", []),
            "discovered_forms": discovery.get("forms", []),
            "discovered_pages": discovery.get("pages", []),
            "test_coverage": test_coverage,
            "findings": run_data.get("insights", {}),
            "bugs": run_data.get("bugs", []),
            "recommendations": run_data.get("recommendations", []),
            "objective_coverage": objective_coverage,
            "report": run_data.get("report"),
            "ai_summary": run_data.get("ai_summary"),
            "ai_report": run_data.get("ai_report", {}),
            "screenshots": run_data.get("screenshot_paths", []),
            "debug_data": run_data,
            "execution_summary": {
                "health_score": run_data.get("health_score", 0),
                "coverage_score": run_data.get("coverage_score", run_data.get("health_score", 0)),
                "confidence_score": run_data.get("confidence_score", 0),
                "objective_pass_rate": run_data.get("objective_pass_rate", 0),
                "scenario_pass_rate": run_data.get("scenario_pass_rate", 0),
                "critical_objective_failures": run_data.get("critical_objective_failures", 0),
            },
            "discovery_status": run_data.get("discovery_status") or plan.get("discovery_status"),
            "discovery_error": run_data.get("discovery_error") or plan.get("discovery_error"),
            "scenario_tree": run_data.get("scenario_tree") or plan.get("scenario_tree") or {},
            "risk_summary": run_data.get("risk_summary") or plan.get("plan_metrics", {}).get("risk_summary", {}),
        }

    manager = BrowserSessionManager(headless=True)
    stabilizer = StabilityService()
    try:
        session = await manager.new_session()
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        return {
            "success": False,
            "status": "failed",
            "failure_reason": "playwright_execution_failed",
            "error": str(exc),
            "traceback": tb
        }

    try:
        await session.page.goto(start_url, wait_until="load", timeout=45000)
        await stabilizer.wait_for_stable(session.page, timeout_ms=8000)
        run_data = await run_agent_loop_v2(
            page=session.page,
            goal=data.goal,
            credentials=data.credentials,
            start_url=start_url,
            max_steps=data.max_steps,
            same_origin_only=data.same_origin_only,
            signals=session.signals,
        )
        # Post-process run into a human-readable AI report (best-effort)
        try:
            report = generate_report(run_data, use_llm=True, user_id=current_user["user_id"], execution_id=run_data.get("run_id"))
        except Exception:
            report = {"error": "report_generation_failed"}

        return {
            "success": run_data.get("status") in {"completed", "completed_with_failures", "max_steps_reached"},
            "status": report.get("status", run_data.get("status")),
            "website_health_score": report.get("website_health_score", 0),
            "workflow_completion": report.get("workflow_completion", 0.0),
            "critical_issues": report.get("critical_issues", 0),
            "high_issues": report.get("high_issues", 0),
            "medium_issues": report.get("medium_issues", 0),
            "low_issues": report.get("low_issues", 0),
            "discovery_status": report.get("discovery_status") or run_data.get("discovery_status"),
            "discovery_error": report.get("discovery_error") or run_data.get("discovery_error"),
            "scenario_tree": report.get("scenario_tree") or run_data.get("scenario_tree") or {},
            "risk_summary": report.get("risk_summary") or run_data.get("risk_summary") or {},
            "ai_report": report.get("ai_report", report),
            "screenshots": report.get("screenshots", []),
            "coverage": report.get("coverage", {}),
            "execution_summary": report.get("execution_summary", {}),
            "debug_data": report.get("debug_data", run_data),
            "run": report.get("execution_summary", {}),
            "report_id": report.get("report_id"),
        }
    finally:
        await session.close()

