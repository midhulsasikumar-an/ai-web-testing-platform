from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.agent.agent_loop_v2 import run_agent_loop_v2
from backend.agent.browser_session import BrowserSessionManager
from backend.agent.services.stability_service import StabilityService
from backend.core.models.agent_state import AgentRunRequest
from backend.events import event_bus
from backend.events.replay_engine import TimelineReplayEngine
from backend.services.ai_report_service import generate_report
from backend.services.auth import get_current_user_from_token

router = APIRouter()


@router.websocket("/ws/live-execution")
async def websocket_live_execution(websocket: WebSocket):
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        await websocket.close(code=4401)
        return
    current_user = get_current_user_from_token(auth_header.split(" ", 1)[1])

    await websocket.accept()
    bus = event_bus
    manager = BrowserSessionManager(headless=True)
    stabilizer = StabilityService()
    session = None
    run_task = None
    subscriber = None
    try:
        payload = await websocket.receive_json()
        request = AgentRunRequest.model_validate(payload)
        run_id = payload.get("run_id") or payload.get("id") or str(uuid.uuid4())
        start_url = str(request.url)
        last_sequence = int(payload.get("last_sequence") or 0)

        subscriber = await bus.subscribe(run_id)

        history = await bus.get_events(run_id)
        history_max_sequence = last_sequence
        for event in history:
            history_max_sequence = max(history_max_sequence, event.sequence)
            if event.sequence > last_sequence:
                await websocket.send_json(event.model_dump(mode="json"))

        session = await manager.new_session()
        await session.page.goto(start_url, wait_until="load", timeout=45000)
        await stabilizer.wait_for_stable(session.page, timeout_ms=8000)

        run_task = asyncio.create_task(
            run_agent_loop_v2(
                page=session.page,
                goal=request.goal,
                credentials=request.credentials,
                start_url=start_url,
                max_steps=request.max_steps,
                same_origin_only=request.same_origin_only,
                signals=session.signals,
                event_bus=bus,
                run_id=run_id,
            )
        )

        while True:
            try:
                event = await asyncio.wait_for(subscriber.get(), timeout=0.5)
                if event.sequence <= history_max_sequence:
                    continue
                history_max_sequence = event.sequence
                await websocket.send_json(event.model_dump(mode="json"))
            except asyncio.TimeoutError:
                if run_task.done() and subscriber.empty():
                    break

        run_data = await run_task
        report = generate_report(run_data, use_llm=True, user_id=current_user["user_id"], execution_id=run_id)
        await websocket.send_json({
            "type": "run_complete",
            "success": run_data.get("status") in {"completed", "max_steps_reached"},
            "run": run_data,
            "ai_report": report,
        })
    except WebSocketDisconnect:
        pass
    finally:
        if subscriber is not None:
            await bus.unsubscribe(run_id, subscriber)
        if session is not None:
            await session.close()


@router.get("/runs/{run_id}/timeline")
async def get_timeline(run_id: str):
    engine = TimelineReplayEngine()
    events = await engine.load(run_id)
    return {"run_id": run_id, "events": [event.model_dump(mode="json") for event in events]}
