# Replay Engine

## Purpose
The replay engine reconstructs an execution timeline from persisted runtime events so the frontend can render a step-by-step run history.

## Implementation
- `TimelineReplayEngine` loads events through the shared event bus.
- Events are persisted as JSONL under `artifacts/timeline/{run_id}/events.jsonl`.
- The replay API exposes the stored events without recomputing the run.

## Timeline Contents
Each recorded step can include:
- screenshot path
- URL
- reasoning
- action payload
- workflow state
- duration
- outcome
- accessibility and performance signals

## Frontend Use
Replay mode can render:
- a step scrubber
- a reasoning timeline
- screenshot snapshots
- failure markers
- workflow transitions

## Notes
Replay is read-only and does not mutate the canonical agent state.