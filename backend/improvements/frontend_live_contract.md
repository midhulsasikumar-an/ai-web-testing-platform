# Frontend Live Contract

## Live Stream
The WebSocket endpoint at `/api/agent/ws/live-execution` streams runtime events directly to the frontend.

## Event Shape
Events follow the canonical `ExecutionEvent` schema and are JSON serializable.

Typical event types:
- `agent_reasoning`
- `action_execution`
- `workflow_transition`
- `bug_detected`
- `screenshot`
- `accessibility_finding`
- `performance_finding`
- `timeline_step`
- `run_status`

## Final Message
When the run completes, the stream emits a `run_complete` message containing:
- the final run payload
- the AI report
- the success flag

## Replay API
The frontend can fetch replay data from:
- `/api/agent/runs/{run_id}/timeline`

## Recommended UI Regions
The frontend can render:
- live event feed
- screenshot strip
- reasoning panel
- workflow visualization
- replay scrubber
- bug cards
- accessibility warnings
- performance warnings

## Compatibility
The existing HTTP agent route remains valid for non-streaming consumers, while the WebSocket route enables live execution views.