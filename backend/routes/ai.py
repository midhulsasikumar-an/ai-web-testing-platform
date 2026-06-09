from fastapi import APIRouter, Depends

from backend.models.ai_schema import AIChatRequest, AIPlanRequest
from backend.services.auth import get_current_user
from backend.services.ai_service import get_ai_response
from backend.services.ai_plan_service import generate_test_plan

router = APIRouter()

@router.post("/chat")
async def chat(data: AIChatRequest, current_user: dict = Depends(get_current_user)):

    ai_response = await get_ai_response(data.message)

    return {
        "response": ai_response
    }


@router.post("/plan")
async def generate_plan(req: AIPlanRequest, current_user: dict = Depends(get_current_user)):
    """Generate an AI test plan for an authenticated user."""
    plan = await generate_test_plan(req.url, req.instruction, req.test_type, credentials=req.credentials)
    return plan
