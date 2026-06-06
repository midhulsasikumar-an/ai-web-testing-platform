# Execution Runtime Pipeline

## Live Pipeline

The execution runtime follows an event-driven loop:

observe -> reason -> validate -> execute -> emit event -> capture artifacts -> analyze -> persist replay -> update frontend -> continue

## Runtime Components

- `backend.agent.agent_loop_v2` for deterministic autonomous execution
- `backend.events.bus.ExecutionEventBus` for async-safe publishing
- `backend.routes.live_execution` for websocket fan-out
- `backend.events.replay_engine.TimelineReplayEngine` for replay loading
- `backend.agent.live_reasoning.engine.LiveReasoningEngine` for narration

## Safeguards

- Monotonic per-run event ordering
- Cached event replay for reconnects
- Persistence to JSONL timeline files
- Shared singleton bus within the process
