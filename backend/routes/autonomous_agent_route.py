from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from backend.agent.agent_loop_v2 import run_agent_loop_v2
from backend.agent.browser_session import BrowserSessionManager
from backend.core.models.agent_state import AgentRunRequest
from backend.services.ai_report_service import generate_report
from backend.agent.services.stability_service import StabilityService
from backend.services.auth import get_current_user

router = APIRouter()


@router.post("/autonomous-test")
async def autonomous_test(data: AgentRunRequest, current_user: dict = Depends(get_current_user)):
    start_url = str(data.url)

    manager = BrowserSessionManager(headless=True)
    stabilizer = StabilityService()
    session = await manager.new_session()
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
            "success": run_data.get("status") in {"completed", "max_steps_reached"},
            "status": report.get("status", run_data.get("status")),
            "website_health_score": report.get("website_health_score", 0),
            "workflow_completion": report.get("workflow_completion", 0.0),
            "critical_issues": report.get("critical_issues", 0),
            "high_issues": report.get("high_issues", 0),
            "medium_issues": report.get("medium_issues", 0),
            "low_issues": report.get("low_issues", 0),
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
