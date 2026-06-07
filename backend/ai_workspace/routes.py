from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.ai_workspace.memory import memory_engine
from backend.ai_workspace.intelligence import delete_memory_by_query, generate_instruction_template, list_memories, resolve_entity_query, resolve_memory_action, save_memory
from backend.ai_workspace.models import (
    ActiveContext,
    BugAnalysisRequest,
    ChatMessage,
    ChatRequest,
    ChatSessionRename,
    InstructionGenerationRequest,
    MemoryCreate,
    MemoryUpdate,
    ReportAnalysisRequest,
    ScreenshotAnalysisRequest,
)
from backend.ai_workspace.retrieval import retrieval_system
from backend.ai_workspace.service import workspace_service
from backend.services.auth import get_current_user

router = APIRouter()


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get("/sessions")
def list_sessions(current_user: dict = Depends(get_current_user)):
    return {"items": memory_engine.list_sessions(current_user["user_id"])}


@router.post("/sessions")
def create_session(payload: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    context = payload.get("active_context") or payload.get("context")
    title = payload.get("title")
    session = memory_engine.get_or_create_session(None, current_user["user_id"], context=context, title=title)
    return {"session": session.model_dump()}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = memory_engine.get_or_create_session(session_id, current_user["user_id"])
    history = memory_engine.get_session_history(session_id, current_user["user_id"], limit=100)
    return {"session": session.model_dump(), "history": history}


@router.patch("/sessions/{session_id}")
def rename_session(session_id: str, payload: ChatSessionRename, current_user: dict = Depends(get_current_user)):
    updated = memory_engine.rename_session(session_id, current_user["user_id"], payload.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    updated.pop("_id", None)
    return {"session": updated}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    deleted = memory_engine.delete_session(session_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ok", "session_id": session_id}


@router.post("/chat")
async def ai_chat(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    session = memory_engine.get_or_create_session(req.session_id, current_user["user_id"], req.context)
    result = await workspace_service.generate_response(
        user_id=current_user["user_id"],
        session_id=session.session_id,
        query=req.message,
        active_context=session.active_context,
    )
    return result


@router.post("/chat/stream")
async def ai_chat_stream(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    session = memory_engine.get_or_create_session(req.session_id, current_user["user_id"], req.context)

    async def events() -> AsyncIterator[str]:
        phases = [
            ("context", "Reading workspace context"),
            ("retrieval", "Retrieving related runs, reports, bugs, and memory"),
            ("model", "Model is responding"),
        ]
        for phase, message in phases:
            yield _sse("status", {"phase": phase, "message": message, "session_id": session.session_id})
            await asyncio.sleep(0.05)

        result = await workspace_service.generate_response(
            user_id=current_user["user_id"],
            session_id=session.session_id,
            query=req.message,
            active_context=session.active_context,
        )

        response_text = str(result.get("response") or "")
        words = response_text.split()
        if words:
            chunk: list[str] = []
            for word in words:
                chunk.append(word)
                if len(chunk) >= 8:
                    yield _sse("delta", {"text": " ".join(chunk) + " "})
                    chunk = []
                    await asyncio.sleep(0.02)
            if chunk:
                yield _sse("delta", {"text": " ".join(chunk)})
        yield _sse("done", result)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/chat/{session_id}/messages")
def list_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    return {"items": memory_engine.get_session_history(session_id, current_user["user_id"], limit=200)}


@router.get("/memory")
def list_memory(current_user: dict = Depends(get_current_user)):
    return {"items": memory_engine.list_memories(current_user["user_id"])}


@router.post("/memory")
def create_memory(payload: MemoryCreate, current_user: dict = Depends(get_current_user)):
    memory = memory_engine.upsert_memory(current_user["user_id"], payload.memory_type, payload.content, payload.importance)
    return {"memory": memory}


@router.patch("/memory/{memory_id}")
def update_memory(memory_id: str, payload: MemoryUpdate, current_user: dict = Depends(get_current_user)):
    updated = memory_engine.update_memory(memory_id, current_user["user_id"], payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"memory": updated}


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    deleted = memory_engine.delete_memory(memory_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"status": "ok", "memory_id": memory_id}


@router.get("/reports/overview")
def reports_overview(
    q: str | None = Query(default=None),
    report_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    return {
        "analysis": retrieval_system.summarize_reports(current_user["user_id"], query=q or "", report_id=report_id),
    }


@router.post("/reports/analyze")
async def analyze_report(payload: ReportAnalysisRequest, current_user: dict = Depends(get_current_user)):
    return await workspace_service.analyze_report(current_user["user_id"], query=payload.query or "", report_id=payload.report_id)


@router.post("/bugs/analyze")
async def analyze_bugs(payload: BugAnalysisRequest, current_user: dict = Depends(get_current_user)):
    return await workspace_service.analyze_bugs(current_user["user_id"], query=payload.query or "")


@router.get("/bugs/overview")
def bugs_overview(current_user: dict = Depends(get_current_user)):
    return {"analysis": retrieval_system.summarize_bugs(current_user["user_id"], query="")}


@router.post("/screenshots/analyze")
async def analyze_screenshots(payload: ScreenshotAnalysisRequest, current_user: dict = Depends(get_current_user)):
    return await workspace_service.analyze_screenshots(
        current_user["user_id"],
        report_id=payload.report_id,
        test_run_id=payload.test_run_id,
    )


@router.get("/screenshots/overview")
def screenshots_overview(
    report_id: str | None = Query(default=None),
    test_run_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    return {"analysis": retrieval_system.summarize_screenshots(current_user["user_id"], report_id=report_id, test_run_id=test_run_id)}


@router.post("/instructions/generate")
async def generate_instruction(payload: InstructionGenerationRequest, current_user: dict = Depends(get_current_user)):
    return await workspace_service.generate_instruction(payload.topic)


@router.get("/recommendations")
async def get_recommendations(current_user: dict = Depends(get_current_user)):
    recs = await workspace_service.get_recommendations(current_user["user_id"])
    return {"recommendations": recs}


@router.get("/context")
def get_context(
    query: str = Query(default=""),
    report_id: str | None = Query(default=None),
    test_run_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    return retrieval_system.get_context(current_user["user_id"], query, report_id=report_id, test_run_id=test_run_id)


@router.get("/resolve/run")
def resolve_run(query: str = Query(default="latest run"), current_user: dict = Depends(get_current_user)):
    return resolve_entity_query(current_user["user_id"], query)


@router.get("/resolve/bug")
def resolve_bug(query: str = Query(default="latest bug"), current_user: dict = Depends(get_current_user)):
    return resolve_entity_query(current_user["user_id"], query)


@router.get("/resolve/screenshot")
def resolve_screenshot(
    query: str = Query(default="latest screenshot"),
    report_id: str | None = Query(default=None),
    test_run_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    return resolve_entity_query(current_user["user_id"], query, report_id=report_id, test_run_id=test_run_id)


@router.get("/analytics/runs")
def run_analytics(current_user: dict = Depends(get_current_user)):
    return resolve_entity_query(
        current_user["user_id"],
        "show regression trend and summarize last 10 runs",
    )


@router.get("/compare/runs")
def compare_runs_natural(
    query: str = Query(default="compare latest run with previous run"),
    current_user: dict = Depends(get_current_user),
):
    return resolve_entity_query(current_user["user_id"], query)
