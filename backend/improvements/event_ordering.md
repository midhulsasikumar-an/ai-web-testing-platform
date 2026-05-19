# Event Ordering

## Ordering Model

Event ordering is enforced per `run_id` using a monotonic sequence counter in the shared event bus.

## Guarantees

- No duplicate sequence assignment from the bus
- Events are persisted in sequence order
- Replay loads are sorted by `(sequence, timestamp)`
- Reconnect streams skip already delivered sequences

## Duplicate Prevention

The websocket consumer tracks a delivered sequence watermark and ignores stale or already delivered events when reconnecting.
