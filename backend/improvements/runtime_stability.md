# Runtime Stability

## Stability Improvements

- Shared singleton event bus for live and replay consumers
- Reconnect-safe websocket delivery with `last_sequence`
- Async-safe event publication and subscriber fan-out
- Persisted event timeline replay for recovery after disconnects
- Monotonic per-run sequence assignment

## Verified Runtime Checks

- `backend.server` imported successfully
- Uvicorn started successfully from the repository root
- Shared bus event ordering check passed
- Websocket route and replay route imported successfully

## Remaining Operational Notes

- Launch the backend from the repository root so package imports resolve cleanly.
- Long-running executions should continue to rely on the shared bus and persisted timeline files rather than process-local websocket state.
