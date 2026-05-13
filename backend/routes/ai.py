from fastapi import APIRouter

from backend.models.ai_schema import AIChatRequest
from backend.services.ai_service import get_ai_response

router = APIRouter()

@router.post("/chat")
async def chat(data: AIChatRequest):

    ai_response = await get_ai_response(data.message)

    return {
        "response": ai_response
    }