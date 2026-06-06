# Replay Verification

## Replay Source

Replay data is loaded from the shared execution event bus and persisted timeline files under `artifacts/timeline/{run_id}/events.jsonl`.

## Replay Guarantees

- Timeline ordering is sequence-based
- Replay is compatible with live websocket events
- Cached events are returned if the process still has them in memory
- Persisted events are reloaded when cache is empty

## Timeline Payload

Replay events use `ExecutionEvent` and include:

- `event_id`
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

## Verification Notes

The replay route `GET /api/agent/runs/{run_id}/timeline` returns the persisted event stream as frontend-ready JSON.
