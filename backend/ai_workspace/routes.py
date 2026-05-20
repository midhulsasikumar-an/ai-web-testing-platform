from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from backend.ai_workspace.models import ChatRequest, WorkflowGenerationRequest
from backend.ai_workspace.memory import memory_engine
from backend.ai_workspace.service import workspace_service
from backend.ai_workspace.retrieval import retrieval_system

router = APIRouter()

@router.post("/chat")
async def ai_chat(req: ChatRequest):
    # Retrieve or create session
    session = memory_engine.get_or_create_session(req.session_id, req.user_id, req.context)
    
    # Generate response
    result = await workspace_service.generate_response(
        user_id=req.user_id,
        session_id=session.session_id,
        query=req.message,
        active_context=session.active_context
    )
    
    return result

@router.get("/session/{session_id}")
def get_session(session_id: str, user_id: str = "demo-user"):
    history = memory_engine.get_session_history(session_id, limit=50)
    session = memory_engine.get_or_create_session(session_id, user_id)
    return {
        "session": session.dict(),
        "history": history
    }

@router.post("/retrieve-report")
def retrieve_report(query: str, user_id: str = "demo-user"):
    reports = retrieval_system.retrieve_reports(user_id, query)
    return {"reports": reports}

@router.post("/compare-runs")
def compare_runs(query: str, user_id: str = "demo-user"):
    runs = retrieval_system.retrieve_reports(user_id, query, limit=2)
    return {"comparisons": runs}

@router.post("/generate-workflow")
async def generate_workflow(req: WorkflowGenerationRequest):
    result = await workspace_service.generate_workflow(req.user_id, req.prompt)
    return result

@router.get("/history")
def get_history(user_id: str = "demo-user"):
    # Return user's long-term memory topics
    return memory_engine.get_user_memory(user_id)

@router.get("/recommendations")
async def get_recommendations(user_id: str = "demo-user"):
    recs = await workspace_service.get_recommendations(user_id)
    return {"recommendations": recs}
