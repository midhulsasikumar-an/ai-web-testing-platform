# Production Scaling Notes

## Browser pooling

The new `BrowserSessionManager` uses a reusable browser process with context-per-run isolation. This is the correct first step because browser launches are expensive, while contexts are cheaper and provide cookie/storage isolation.

Next steps:

- add max concurrent contexts
- add per-domain concurrency limits
- add idle browser recycling
- add crash detection and browser restart
- persist optional storage state per project/user

## Queue-based execution

FastAPI request/response is not enough for long autonomous runs. Production should move agent execution into a worker queue:

- API creates `AgentRun`
- worker consumes run
- browser session executes steps
- progress streams over WebSocket/SSE
- user can cancel the run
- run heartbeat detects stuck workers

Suitable queue options include Celery, RQ, Dramatiq, Arq, or a managed cloud queue.

## Distributed execution

For enterprise scale:

- run browser workers separately from API servers
- shard by user, project, or domain
- store artifacts in object storage
- store run/step state in MongoDB
- use Redis for queues, rate limits, and cancellation
- enforce per-tenant budgets

## Observability

Add structured telemetry:

- OpenTelemetry spans per run, step, LLM call, observation, selector resolution, action execution, and recovery
- metrics for action success rate, retry rate, timeout rate, blocked policy rate, average step duration, browser memory usage, and LLM latency
- JSON logs with `run_id`, `step`, `url`, `action`, `failure_type`, and `selector_used`
- HAR capture or Playwright tracing for high-value failed runs

## Cost and timeout budgets

Production runs need budgets:

- max steps
- max wall-clock time
- max navigation depth
- max LLM calls
- max screenshots/artifact size
- max retries per action
- max pages visited

The refactor adds max steps and retries. Wall-clock budgets and cancellation should be added with queue workers.

## Database model direction

Persist these collections:

- `agent_runs`
- `agent_steps`
- `agent_artifacts`
- `agent_memory_events`
- `selector_stats`
- `site_maps`
- `bug_reports`

Do not persist only final summaries. Real autonomous QA needs replayable evidence.
