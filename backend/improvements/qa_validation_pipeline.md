# QA Validation Pipeline

Pipeline:
- Executor produces artifacts (DOM, console, network, screenshots, cookies)
- `WebsiteHealthService` aggregates detectors to produce a health score
- `BugDetectionService` converts detector outputs into classified issues
- `GoalCompletionService` returns nuanced workflow states
- `FormFuzzingService` exercises forms and reports validation behavior

Integration notes:
- All detectors expect an `artifacts` dict produced by `test_runner.run_test`.
- The orchestrator `test_services.run_test_and_update` composes the final AI report.
