from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException

from backend.events.bus import event_bus
from backend.events.schemas import ExecutionEvent
from backend.multi_agent.models import MultiAgentRunRequest
from backend.multi_agent.orchestrator import MultiAgentOrchestrator
from backend.services.auth import get_current_user, get_current_user_from_token
from backend.database.mongo import collection as test_runs_collection

logger = logging.getLogger("routes.multi_agent")
router = APIRouter()


@router.post("/multi-agent/run")
async def run_multi_agent(request: MultiAgentRunRequest, current_user: dict = Depends(get_current_user)):
    orchestrator = MultiAgentOrchestrator()
    return await orchestrator.run(request)


@router.websocket("/ws/multi-agent-execution")
async def websocket_multi_agent_execution(websocket: WebSocket):
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        await websocket.close(code=4401)
        return
    try:
        current_user = get_current_user_from_token(auth_header.split(" ", 1)[1])
    except HTTPException:
        await websocket.close(code=4401)
        return
    user_id = str(current_user.get("user_id") or current_user.get("id") or "")

    await websocket.accept()
    orchestrator = MultiAgentOrchestrator()
    subscriber = None
    run_task = None
    run_id = str(uuid.uuid4())
    try:
        payload = await websocket.receive_json()
        request = MultiAgentRunRequest.model_validate(payload)
        run_id = request.run_id or str(uuid.uuid4())
        request.run_id = run_id

        requested_test_id = str(payload.get("test_id") or "").strip()
        if requested_test_id:
            owner = test_runs_collection.find_one(
                {"test_id": requested_test_id, "user_id": user_id},
                {"_id": 1},
            )
            if not owner:
                await websocket.send_json({
                    "type": "error",
                    "run_id": run_id,
                    "message": "Forbidden: test_id does not belong to the authenticated user.",
                })
                await websocket.close(code=4403)
                return
        last_sequence = int(payload.get("last_sequence") or 0)

        subscriber = await event_bus.subscribe(run_id)
        for event in await event_bus.get_events(run_id):
            if event.sequence > last_sequence:
                await websocket.send_json(event.model_dump(mode="json"))
                last_sequence = event.sequence

        run_task = asyncio.create_task(orchestrator.run(request))
        while True:
            try:
                event = await asyncio.wait_for(subscriber.get(), timeout=0.5)
                if event.sequence <= last_sequence:
                    continue
                last_sequence = event.sequence
                await websocket.send_json(event.model_dump(mode="json"))
            except asyncio.TimeoutError:
                if run_task.done() and subscriber.empty():
                    break

        result = await run_task
        await websocket.send_json({
            "type": "run_complete",
            "run_id": run_id,
            "status": result.get("status"),
            "report": result.get("report"),
        })
    except WebSocketDisconnect:
        pass
    finally:
        if subscriber is not None:
            await event_bus.unsubscribe(run_id, subscriber)