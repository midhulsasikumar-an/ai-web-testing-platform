from fastapi import APIRouter

from backend.models.ai_schema import AIChatRequest, AIPlanRequest
from backend.services.ai_service import get_ai_response
from backend.services.ai_plan_service import generate_test_plan

router = APIRouter()

@router.post("/chat")
async def chat(data: AIChatRequest):

    ai_response = await get_ai_response(data.message)

    return {
        "response": ai_response
    }


@router.post("/plan")
async def generate_plan(req: AIPlanRequest):
    """Generate an AI test plan. This endpoint is intentionally public to allow
    interactive plan generation from the UI without requiring authentication.
    If you want to restrict this in production, re-enable the auth dependency.
    """
    plan = await generate_test_plan(req.url, req.instruction, req.test_type, credentials=req.credentials)
    return plan
