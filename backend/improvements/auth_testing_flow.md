# Authentication Testing Flow

- Intent: verify protected routes, session persistence, logout, invalid credentials handling.
- Executor should mark auth intent and provide expectations (e.g., `cookie_exists`, `dom_contains`).
- SuccessDetector will assert cookies and protected content.
- NetworkAnalysisService will surface failed auth requests (401/403) as issues.
