from fastapi import APIRouter

from backend.models.ai_schema import AIChatRequest
from backend.services.ai_service import get_ai_response
from backend.services.dom_service import extract_page_elements
from backend.services.execution_service import run_test_steps
from backend.services.judgement_service import analyze_test_results
from backend.services.planning_service import generate_test_plan
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

    dom = await extract_page_elements(url)

    test_plan = await generate_test_plan(url, dom)

    return test_plan

@router.post("/execute")
async def execute_test(payload: ExecuteRequest):
    url = payload.url
    test_case = payload.test_case

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
            "ai_analysis": ai_analysis
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }