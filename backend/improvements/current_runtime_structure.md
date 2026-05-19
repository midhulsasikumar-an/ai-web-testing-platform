# Current Runtime Structure

- `backend/agent/agent_loop_v2.py` — single orchestrator loop used for all runs.
- `backend/events/bus.py` — central event bus singleton for replay and live streaming.
- `backend/runtime/session_manager.py` — in-memory session tracking with lightweight persistence.
- `backend/routes/runtime.py` — websocket and control APIs for runtime.
- `artifacts/` — local artifact storage for screenshots, timelines, and session files.
# Current Runtime Structure

- `backend/agent/` - agent orchestration and services
- `backend/storage/` - artifact persistence helpers
- `backend/improvements/` - design and operational docs

Use these docs as the canonical reference when extending detectors or reporters.
