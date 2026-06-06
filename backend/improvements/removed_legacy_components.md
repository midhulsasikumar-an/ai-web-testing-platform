# Removed Legacy Components

The following legacy and duplicate components were removed to simplify the backend:

- `legacy/` directory (old loops, adapters, and legacy services)
- Duplicate model mirrors (`backend.agent.schemas` and others)
- Old websocket and replay endpoints replaced by unified `event_bus` and `/ws/runtime/{execution_id}`

This reduces confusion and keeps a single canonical execution path.
# Removed Legacy Components

Document any removed or deprecated modules here.

When performing cleanup, update this file with details of removed files and rationale.
