from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.events.bus import event_bus
from backend.events.schemas import ExecutionEvent
from backend.multi_agent.models import MultiAgentRunRequest
from backend.multi_agent.orchestrator import MultiAgentOrchestrator

router = APIRouter()


@router.post("/multi-agent/run")
async def run_multi_agent(request: MultiAgentRunRequest):
    orchestrator = MultiAgentOrchestrator()
    return await orchestrator.run(request)


@router.websocket("/ws/multi-agent-execution")
async def websocket_multi_agent_execution(websocket: WebSocket):
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