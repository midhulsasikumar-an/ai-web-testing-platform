# Event Pipeline

## Event Bus
`backend/events/bus.py` implements the canonical execution event bus.

Capabilities:
- async-safe publish and subscribe
- multiple subscribers per run
- in-memory event replay
- timeline persistence to JSONL
- support for WebSocket broadcasting

## Event Model
`backend/events/schemas.py` defines `ExecutionEvent` and `ExecutionEventType`.

Each event contains:
- `run_id`
- `type`
- `message`
- `timestamp`
- `sequence`
- `workflow_state`
- `action`
- `screenshot`
- `severity`
- `confidence`
- `url`
- `payload`

## Persistence
Events are written to:
- `artifacts/timeline/{run_id}/events.jsonl`

This keeps the stream replayable and durable without changing the agent state model.

## Publishing Points
The agent loop now emits events for:
- initial run start
- reasoning narration
- selected actions
- screenshot capture
- accessibility findings
- workflow transitions
- detected bugs
- completion and termination

## Replay Support
`backend/events/replay_engine.py` reads persisted events and exposes them for replay or API retrieval.