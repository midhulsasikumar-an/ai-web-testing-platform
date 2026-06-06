# Runtime Execution Flow

1. Client requests an execution run (existing start endpoints).
2. `agent_loop_v2.run` creates a session via `session_manager` and publishes initial `RUN_STATUS` to `event_bus`.
3. Frontend connects to `/ws/runtime/{execution_id}` to receive replayed events and live updates.
4. Agent publishes events (reasoning, action_started/completed, screenshot, workflow transitions, bug detections) to `event_bus`.
5. Events are persisted to `artifacts/timeline/{execution_id}/events.jsonl` and streamed to subscribers.
6. Client can cancel via `POST /api/runtime/{execution_id}/cancel` which marks session cancelled and publishes a `RUN_STATUS` event.
# Runtime Execution Flow

Describe the full integrated pipeline:

1. observe -> planner -> execute -> capture artifacts
2. validate -> success detection -> website health analysis
3. visual, network, bug detection -> goal completion evaluation
4. persist artifacts -> generate frontend-ready AI report

Services ownership:
- Execution: `backend/services/test_runner.py`
- Orchestration: `backend/services/test_services.py`
- QA Detectors: `backend/agent/services/*`
- Artifact storage: local `artifacts/` mounted at `/artifacts`
