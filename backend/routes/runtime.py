from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from backend.events.bus import event_bus
from backend.events.schemas import ExecutionEvent, ExecutionEventType
from backend.runtime.session_manager import session_manager

router = APIRouter()


@router.websocket("/ws/runtime/{execution_id}")
async def runtime_ws(websocket: WebSocket, execution_id: str, last_sequence: Optional[int] = 0):
    await websocket.accept()
    queue = await event_bus.subscribe(execution_id)
    try:
        # Replay history greater than last_sequence
        events = await event_bus.get_events(execution_id)
        for ev in events:
            if ev.sequence > (int(last_sequence) or 0):
                etype = ev.type.value
                # normalize to frontend-friendly types
                mapping = {
                    "agent_reasoning": "reasoning",
                    "action_execution": "action_started",
                    "timeline_step": "action_completed",
                    "workflow_transition": "workflow_transition",
                    "bug_detected": "bug_detected",
                    "screenshot": "screenshot",
                    "run_status": "run_status",
                }
                await websocket.send_json({
                    "event_type": mapping.get(etype, etype),
                    "message": ev.message,
                    "workflow_state": ev.workflow_state,
                    "sequence": ev.sequence,
                    "timestamp": ev.timestamp.isoformat(),
                    "payload": ev.payload,
                    "screenshot": ev.screenshot,
                })

        # Stream live events
        while True:
            ev: ExecutionEvent = await queue.get()
            etype = ev.type.value
            mapping = {
                "agent_reasoning": "reasoning",
                "action_execution": "action_started",
                "timeline_step": "action_completed",
                "workflow_transition": "workflow_transition",
                "bug_detected": "bug_detected",
                "screenshot": "screenshot",
                "run_status": "run_status",
            }
            await websocket.send_json({
                "event_type": mapping.get(etype, etype),
                "message": ev.message,
                "workflow_state": ev.workflow_state,
                "sequence": ev.sequence,
                "timestamp": ev.timestamp.isoformat(),
                "payload": ev.payload,
                "screenshot": ev.screenshot,
            })

    except WebSocketDisconnect:
        await event_bus.unsubscribe(execution_id, queue)
    except Exception:
        await event_bus.unsubscribe(execution_id, queue)
        raise


@router.post("/api/runtime/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    ok = await session_manager.cancel(execution_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Execution not found")
    # publish run status
    await event_bus.publish(ExecutionEvent(run_id=execution_id, type=ExecutionEventType.RUN_STATUS, message="Execution cancelled"))
    return {"execution_id": execution_id, "status": "CANCELLED"}
