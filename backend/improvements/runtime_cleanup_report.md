# Runtime Cleanup Report

## Scope
A conservative runtime scan of the backend was performed with emphasis on import usage and route wiring. No runtime-critical files were removed.

## Findings

### Compatibility shims still used at runtime
These files look like legacy namespaces, but they are still imported by live code and must remain until callers are migrated:
- `backend/models/schema.py` is imported by `backend/server.py` and `backend/services/test_runner.py`.
- `backend/models/ai_schema.py` is imported by `backend/routes/ai.py`.
- The `backend/models/*` package therefore behaves as a compatibility layer, not dead code.

### Legacy execution path still active
- `backend/services/execution_service.py` is still imported by `backend/routes/ai.py`.
- It should not be deleted yet because the AI route still depends on it.
- The newer autonomous runtime uses `backend/agent/agent_loop_v2.py`, but the older test runner route remains operational.

### Scoring/reporting helpers still referenced
- `backend/services/test_services.py` still imports the scoring helpers under `backend/services/scoring/*`.
- That pipeline is still part of the application startup/runtime path and is not safe to remove without a route migration.

### Canonical architecture in use
- The autonomous backend now uses canonical models under `backend.core.models.*` for the upgraded agent/runtime flow.
- The newer autonomous QA path is anchored in `backend/agent/agent_loop_v2.py`, `backend/agent/planner/*`, and `backend/services/ai_report_service.py`.

## Cleanup Candidates
These are not removed because they still have live references or may be needed for compatibility, but they are the best candidates for future consolidation:
- `backend/services/execution_service.py`
- `backend/services/test_services.py`
- `backend/services/scoring/*`
- `backend/models/*` compatibility shims

## Duplicate Architecture Notes
- There are still two report-oriented paths in the codebase:
  - the legacy test pipeline under `backend/services/test_services.py`
  - the autonomous QA pipeline under `backend/services/ai_report_service.py`
- This is acceptable for now because they serve different routes, but the legacy route should be retired only after downstream consumers are migrated.

## Recommended Next Steps
1. Migrate any remaining `/api/ai` consumers to the canonical autonomous QA report pipeline.
2. Keep the compatibility shims until that migration is complete.
3. Re-run import usage scans after route migration, then remove dead helpers only if they no longer appear in runtime imports.
