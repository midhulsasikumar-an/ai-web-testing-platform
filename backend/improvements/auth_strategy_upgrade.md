Authentication strategy upgrade

Overview
- Added a ranked authentication strategy layer that chooses between login, signup, OAuth, guest access, and skip-auth modes before the first auth action executes.
- Strategy is computed from credentials, goal intent, current workflow state, route classification, and existing session signals.

Production behavior
- Credentials provided: prefer `LOGIN_EXISTING_USER`, suppress signup, and keep the workflow locked to login unless recovery or route adaptation is required.
- No credentials provided and auth required: prefer `CREATE_NEW_ACCOUNT` when signup is available, generate temporary credentials, and continue authenticated exploration after verification.
- Already authenticated: skip auth and continue the workflow immediately.

Integration points
- `backend/core/models/auth.py` defines the canonical auth strategy models.
- `backend/agent/services/auth_strategy_service.py` ranks strategies and classifies auth routes.
- `backend/agent/planner/__init__.py` and `backend/agent/planner/login_planner.py` consume the selected strategy.
- `backend/agent/skills/authenticate.py` applies the same strategy in skill-based execution.
- `backend/services/ai_report_service.py` now includes semantic auth summaries in the final report.

Verification
- Static validation passed for all touched modules.
- Direct behavior check confirmed:
  - credentials provided -> `LOGIN_EXISTING_USER`
  - no credentials on signup route -> `CREATE_NEW_ACCOUNT`
  - already authenticated -> `GUEST_ACCESS` with `SKIP_AUTH_MODE`
