Reporting pipeline

1. Autonomous agent finishes and returns structured execution JSON.
2. Route calls `generate_report(run_data, use_llm=True)`.
3. `execution_analysis_service.analyze_execution` extracts summary, timeline, issues.
4. `ai_report_service` builds deterministic narrative and structured model.
5. `report_llm_service.enhance_narrative` optionally improves narrative.
6. `report_repository.save_report` persists the final report document.
7. Route returns `ai_report` alongside original `run` for compatibility.

Error handling:
- Any failure in the reporting layer is caught; the route still returns the raw execution result.
- A minimal fallback report is persisted when full report generation fails.
