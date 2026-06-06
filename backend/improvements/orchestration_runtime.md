# Orchestration Runtime

## Runtime Flow

The orchestrator coordinates browser-backed and analysis-only agents through a shared runtime context.

## Behavior

- Auth can run sequentially to seed shared browser state.
- Navigation and analysis agents can run concurrently.
- Parallel failures are isolated per agent and converted into structured failure results.
- Each agent emits live reasoning, bug, and status events to the shared bus.

## Entry Points

- HTTP: `POST /api/agent/multi-agent/run`
- WebSocket: `/api/agent/ws/multi-agent-execution`

## Stability Notes

- The orchestrator uses a shared browser manager and async-safe memory.
- Execution state is persisted as timeline events and a unified report.
