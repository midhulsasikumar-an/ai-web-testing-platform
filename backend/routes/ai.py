from fastapi import APIRouter, Depends

from backend.models.ai_schema import AIChatRequest, AIPlanRequest
from backend.services.auth import get_current_user
from backend.services.ai_service import get_ai_response
from backend.services.ai_plan_service import generate_test_plan, build_executable_test_case
from backend.services.dom_service import extract_page_elements
from backend.services.execution_service import run_test_steps
from backend.services.judgement_service import analyze_test_results
from backend.services.action_translation_service import translate_test_case
# Legacy planning_service has been archived. Planning endpoints are deprecated.
from backend.ai.schema.test_plan_schema import ExecuteRequest

router = APIRouter()

@router.post("/chat")
async def chat(data: AIChatRequest):

    ai_response = await get_ai_response(data.message)

    return {
        "response": ai_response
    }

@router.get("/analyze")
async def analyze(url: str):

    data = await extract_page_elements(url)

    return data

@router.get("/plan")
async def plan(url: str):
    return {"error": "use POST /ai/plan with instruction and url"}


@router.post("/plan")
async def generate_plan(req: AIPlanRequest):
    """Generate an AI test plan. This endpoint is intentionally public to allow
    interactive plan generation from the UI without requiring authentication.
    If you want to restrict this in production, re-enable the auth dependency.
    """
    plan = await generate_test_plan(req.url, req.instruction, req.test_type)
    return plan

@router.post("/execute")
async def execute_test(payload: ExecuteRequest):
    url = payload.url
    test_case, translation_logs = translate_test_case(payload.test_case)

    if not url or not test_case:
        return {
            "error": "url and test_case are required"
        }

    try:
        # ---------------------------
        # STEP 1: Extract DOM
        # ---------------------------
        dom = await extract_page_elements(url)

        # ---------------------------
        # STEP 2: Run execution engine
        # ---------------------------
        result = await run_test_steps(
            url=url,
            test_case=test_case,
            dom=dom
        )

        ai_analysis = await analyze_test_results(result)

        return {
            "success": True,
            "url": url,
            "result": result,
            "translation_logs": translation_logs,
            "ai_analysis": ai_analysis
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }