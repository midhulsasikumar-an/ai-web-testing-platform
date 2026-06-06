# Performance Analysis

## Purpose
The performance analyzer extracts deterministic health signals from the execution trace.

## Location
- `backend/services/performance_analysis_service.py`

## Signals
- slow actions or delayed steps
- console performance warnings
- potential long-task indicators
- hydration or layout-shift warning text
- memory-spike risk heuristics

## Output
The analyzer returns:
- `performance_score`
- `findings`
- `slow_api_risk`
- `console_performance_risk`
- `memory_spike_risk`
- `layout_shift_risk`

## Runtime Integration
Performance findings are included in:
- live events
- run summary
- AI report sections

## Goal
Surface actionable performance regressions without depending on a heavyweight profiler in the first release.