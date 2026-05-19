# Frontend Integration Contract

WebSocket: `/ws/runtime/{execution_id}`

Messages (JSON):

- `event_type`: one of `reasoning`, `action_started`, `action_completed`, `screenshot`, `workflow_transition`, `bug_detected`, `execution_completed`, `execution_failed`, `run_status`
- `message`: human readable narrative
- `workflow_state`: canonical workflow state string
- `sequence`: monotonic event sequence
- `timestamp`: ISO8601 timestamp
- `payload`: additional structured data
- `screenshot`: optional path under `/artifacts` or `/screenshots`

Cancel API:

POST `/api/runtime/{execution_id}/cancel` -> { `execution_id`, `status`: `CANCELLED` }
