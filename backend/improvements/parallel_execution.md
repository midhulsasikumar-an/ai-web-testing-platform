# Parallel Execution

## Runtime Behavior

The orchestrator uses async concurrency for non-dependent agents. When auth/session seeding is required, authentication runs first and the rest of the agents fan out against the shared state snapshot.

## Stability Guarantees

- one agent failure does not cancel the entire run
- each agent returns a structured result
- shared state writes are serialized via locks
- websocket updates remain ordered via the shared event bus
