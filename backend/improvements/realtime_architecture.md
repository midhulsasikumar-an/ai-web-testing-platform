# Realtime Architecture

## Overview
The autonomous agent now supports an opt-in realtime execution stream layered on top of the canonical runtime. The existing HTTP run path remains intact, while a WebSocket route streams live execution events during a run.

## Core Pieces
- `backend/events/schemas.py` defines the event contract.
- `backend/events/bus.py` provides an async-safe pub/sub bus with persistence.
- `backend/routes/live_execution.py` exposes the WebSocket entrypoint and replay route.
- `backend/agent/agent_loop_v2.py` publishes reasoning, action, workflow, accessibility, screenshot, and completion events.

## Runtime Flow
1. The client opens the WebSocket and sends an `AgentRunRequest` payload.
2. The backend creates a browser session, event bus, and run id.
3. `run_agent_loop_v2` executes the canonical agent loop.
4. The loop publishes events as semantic state changes occur.
5. The WebSocket forwards events to the frontend in real time.
6. The bus persists events to `artifacts/timeline/{run_id}/events.jsonl` for replay.

## Event Classes
- `agent_reasoning`
- `action_execution`
- `workflow_transition`
- `bug_detected`
- `screenshot`
- `accessibility_finding`
- `performance_finding`
- `timeline_step`
- `run_status`

## Compatibility
- The existing `/api/agent/autonomous-test` HTTP route still returns the final report after completion.
- Realtime streaming is additive and does not change the deterministic orchestration path.