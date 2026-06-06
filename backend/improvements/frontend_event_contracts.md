# Frontend Event Contracts

## Live Event Schema

All runtime events are emitted as `ExecutionEvent` objects.

### Core fields

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

## Event Types

- `agent_reasoning`
- `action_execution`
- `workflow_transition`
- `bug_detected`
- `screenshot`
- `accessibility_finding`
- `performance_finding`
- `timeline_step`
- `run_status`
- `replay_event`

## Frontend Views Supported

- Live execution feed
- AI reasoning panel
- Screenshot viewer
- Bug timeline
- Workflow graph
- Execution statistics
- Replay mode

## Artifact URLs

- Screenshots are served from `/screenshots/...`
- Timeline artifacts are persisted under `/artifacts/...`
- Replay fetches use `GET /api/agent/runs/{run_id}/timeline`
