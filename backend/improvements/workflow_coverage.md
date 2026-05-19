# Workflow Coverage

## Coverage Signals

The coverage engine tracks:

- routes explored
- forms tested
- APIs triggered
- interactions performed
- accessibility findings
- performance findings

## Scoring

Coverage is computed from the distinct routes, forms, APIs, and interactions observed during execution. Accessibility and performance signals adjust the score downward when issues are detected.

## Runtime Contract

Coverage snapshots are attached to the unified report and can be rendered directly by the frontend to show exploration depth and testing breadth.
# Workflow Coverage

Track pages visited, forms tested, modules explored, and compute a coverage score.

Implementation notes:
- Executor should emit visited route list and action types.
- Coverage aggregator maps visited routes to known app routes and computes risk areas.
