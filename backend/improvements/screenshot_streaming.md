# Screenshot Streaming

## Screenshot Flow

When a screenshot is captured during execution, it should be:

1. Persisted locally as an artifact
2. Added to the execution timeline event payload
3. Broadcast to websocket subscribers
4. Included in replay persistence
5. Attached to bug and report summaries

## Frontend Consumption

Use the screenshot URL from the event payload or the persisted report data. The frontend should treat screenshot events as immutable timeline anchors and render them in step order.

## Contract

- Artifact path should be stable and relative
- Screenshot events should include the artifact URL in `screenshot`
- Screenshot events should also include the step context in `payload`
