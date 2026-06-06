# Authentication Testing Pipeline

- Executor should flag auth-related scenarios with metadata.intent = 'login' or 'signup'.
- `SuccessDetector` checks for cookies and protected DOM content after login.
- `NetworkAnalysisService` flags 401/403 responses during auth flows.
- `BugDetectionService` escalates auth bypass and session failures to critical.
