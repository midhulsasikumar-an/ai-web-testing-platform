# Websocket Runtime Verification

## Verified Runtime Path

The live execution websocket uses a shared process-wide event bus and streams execution-scoped events from `backend.routes.live_execution.websocket_live_execution`.

## Verified Properties

- Stable websocket acceptance and disconnect handling
- Async-safe publish/subscribe fan-out
- Multiple subscribers per `run_id`
- Shared event bus across live stream and replay consumers
- Reconnect-safe event delivery using `last_sequence`
- Execution-scoped channels keyed by `run_id`

## Delivery Contract

Clients connect and send an initial JSON payload compatible with `AgentRunRequest`. Optional fields:

- `run_id`: reuse an existing execution stream
- `last_sequence`: resume from a known event sequence

The server replays missed cached events from the shared bus and then streams new events live.

## Event Ordering

The event bus assigns monotonic per-run sequence numbers. Events are persisted and streamed in sequence order.

## Runtime Verification

- `backend.server` import: passed
- Uvicorn startup: passed
- Shared event bus wiring: passed
- Replay path wiring: passed
