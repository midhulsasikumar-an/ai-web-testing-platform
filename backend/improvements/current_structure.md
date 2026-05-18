# Backend Current Structure

This file documents the actual behaviour and integration status of the important backend files discovered during the audit. Entries only describe code that exists in the repository and trace real imports/usages.

---

## File Path
backend/server.py

## Purpose
Application entrypoint: mounts FastAPI app and includes routers.

## Used By
Run as top-level module (uvicorn). Imports all route modules, DB collections.

## Depends On
backend.routes.*, backend.database.mongo, backend.services.*

## Runtime Critical?
YES

## Status
Active

## Problems
- Exposes two autonomous flows (`/ai/autonomous` and `/api/agent`) that use different architectures (legacy services pipeline vs agent v2). This increases maintenance surface.

## Recommended Action
- Keep, but document and consolidate routing to a single maintained path (prefer `agent_loop_v2`).

---

## File Path
backend/routes/autonomous_agent_route.py

## Purpose
FastAPI POST route `/api/agent/autonomous-test` that creates a browser session and calls `run_agent_loop_v2`.

## Used By
`backend/server.py` (registered under `/api/agent`).

## Depends On
`backend.agent.browser_session.BrowserSessionManager`, `backend.agent.agent_loop_v2.run_agent_loop_v2`

## Runtime Critical?
YES

## Status
Active

## Problems
- Correctly awaits session creation and closes context, but does not call `BrowserSessionManager.shutdown()` on app shutdown (process-level resource management omission).

## Recommended Action
- Keep and add app-lifespan shutdown hook to call `BrowserSessionManager.shutdown()`.

---

## File Path
backend/agent/agent_loop_v2.py

## Purpose
Primary orchestration loop used by the `autonomous-agent` route. Integrates observer, planner (skill engine + legacy planners), validator, executor, recovery, memory, world model, and observability.

## Used By
`backend.routes.autonomous_agent_route.autonomous_test`

## Depends On
Many subsystems under `backend.agent.*` and `backend.observability` and `backend.config.agent_config`.

## Runtime Critical?
YES

## Status
Active, central orchestrator

## Problems
- Mixes two model namespaces: constructs `SkillContext` using `backend.agent` types but `SkillContext` (and many skill engine types) expect `backend.core.models` types — a duplication/incompatibility risk (see architecture audit).
- Recovery logic in `RecoveryEngine` may retry original actions by calling `executor.execute` without re-running the validator, allowing validator bypass.
- Memory is purely in-process (`AgentMemory`) — no persistence layer; this is by design but must be documented (not durable across runs).

## Recommended Action
- Keep; immediately address model namespace inconsistencies and enforce validator re-check before recovery retries.

---

## File Path
backend/agent/browser_session.py

## Purpose
Playwright session pool manager. Creates a browser once (class-level), provides per-run contexts and pages. Collects basic browser signals.

## Used By
Routes and tests that instantiate browser contexts (routes, agent loop).

## Depends On
`playwright.async_api`

## Runtime Critical?
YES

## Status
Active

## Problems
- `new_session()` opens contexts and pages correctly; `BrowserSession.close()` closes only the context (not the browser). The module never registers a shutdown hook to call `shutdown()`; long-running processes will keep the browser process alive until Python exits.

## Recommended Action
- Keep; add application-level lifecycle management to call `BrowserSessionManager.shutdown()` on shutdown.

---

## File Path
backend/agent/observer.py

## Purpose
Observes the page, extracts DOM elements, forms, headings, text, screenshots, and produces `Observation` objects.

## Used By
`agent_loop_v2`, `agent_loop` and recovery flows.

## Depends On
`playwright.async_api.Page`, `backend.agent.selector_engine`.

## Runtime Critical?
YES

## Status
Active

## Problems
- JS extraction script and fingerprint logic are robust; no major issues. Uses blocking file system calls inside async functions to write screenshots (minor risk of blocking event loop briefly).

## Recommended Action
- Keep; consider using threads or aiofiles for heavy disk I/O if scale matters.

---

## File Path
backend/agent/executor.py

## Purpose
Performs Playwright-driven action execution (navigate, click, fill, select, scroll, etc.), handles retries of selector candidates and screenshots artifacts.

## Used By
`agent_loop_v2`, `agent_loop`, `recovery_engine` (retry), tests.

## Depends On
`backend.agent.selector_engine`, `playwright.async_api`.

## Runtime Critical?
YES

## Status
Active

## Problems
- Correct async Playwright usage. Returns structured `ActionResult` objects.
- Risk: called directly by `RecoveryEngine` retry code without re-validation (validator bypass).

## Recommended Action
- Keep, but require post-recover validation or re-run validator prior to retry execution.

---

## File Path
backend/agent/validator/action_validator.py

## Purpose
Validates proposed actions against policy, confidence thresholds, and observation state.

## Used By
`agent_loop_v2` and `agent_loop` (validator.validate calls). Re-exported via `backend/agent/action_validator.py`.

## Depends On
`backend.agent.safety.SafetyPolicy`, `backend.agent.memory_service.AgentMemory`.

## Runtime Critical?
YES

## Status
Active

## Problems
- Functionally sound. No enforcement layer prevents other code paths (e.g., recovery retries) from calling the executor directly.

## Recommended Action
- Keep; make validator a mandatory pre-execution check or centralize executor invocation through a validated wrapper.

---

## File Path
backend/agent/recovery/recovery_engine.py

## Purpose
Implements recovery decisioning and local recovery strategies (dismiss modals, refresh, retry selectors, wait for stability).

## Used By
`agent_loop_v2`, `agent_loop`

## Depends On
`backend.agent.executor.ActionExecutor`, `backend.agent.observer.BrowserObserver`

## Runtime Critical?
YES

## Status
Active

## Problems
- `recover()` may call `executor.execute()` directly to retry the original action without re-running the action validator. This allows riskier actions to be retried without enforcement.

## Recommended Action
- Modify `recover()` to re-validate actions (or call executor via a validated entrypoint) before retrying originals. Add limits and explicit escalation for repeated retries.

---

## File Path
backend/agent/memory_service.py

## Purpose
In-run agent memory (episodic records, selector memory, visited sequences, loop detection heuristics).

## Used By
Planners, validator, loop prevention, recovery, trajectory engine.

## Depends On
`backend.agent.schemas` models, selector memory component.

## Runtime Critical?
YES (for agent decisioning)

## Status
Active (in-memory only)

## Problems
- Memory is ephemeral (not persisted). `compact_for_llm()` exists but there is no backing persistent store — acceptable for single-run, but not durable.

## Recommended Action
- Keep; optionally add a pluggable persistence adapter (mongo/postgres) for long-term analysis and multi-run learning.

---

## File Path
backend/agent/planner/__init__.py and planner/base_planner.py (+ login/exploration/regression planners)

## Purpose
Legacy planner implementations used as fallback when the skill engine is disabled or not applicable.

## Used By
`agent_loop_v2` (fall back to `PlannerOrchestrator`), `agent_loop`.

## Depends On
`backend.agent.memory_service.AgentMemory`, `backend.agent.services.frontier_service`

## Runtime Critical?
YES (fallback)

## Status
Active

## Problems
- Functionality is concrete and used. However there is duplicate planning infrastructure in `backend/services/planning_service.py` that implements an LLM-driven planner used by a separate route.

## Recommended Action
- Merge planning responsibilities or clearly separate the two flows (legacy LLM services vs agent v2). Prefer consolidating to the agent v2 planners/skill-engine.

---

## File Path
backend/services/planning_service.py

## Purpose
Legacy LLM-based test-plan generator (uses external Groq client). Called by `/ai/autonomous/full-test` route.

## Used By
`backend.routes.autonomous.full_test`

## Depends On
`groq` client, `backend.services.dom_service` output

## Runtime Critical?
NO (alternate architecture)

## Status
Active (but separate/duplicated planning path)

## Problems
- External dependency on `GROQ_API_KEY` and Groq SDK. Not integrated with v2 agent components. Represents a parallel legacy architecture.

## Recommended Action
- MERGE or DEPRECATE: pick a single planning path. If LLM-driven planning is required, wrap it as an optional plugin invoked by the v2 skill/planner architecture.

---

## File Path
backend/agent/skill_engine/* and backend/agent/skills/*

## Purpose
Skill engine: dynamic skill registry, selector, router and concrete skills implementing common flows (authenticate, dismiss modal, complete form, navigate sidebar, etc.).

## Used By
`agent_loop_v2` (skill_router used for skill-based planning when enabled)

## Depends On
Mixture of `backend.core.models.*` and `backend.agent.services.*`

## Runtime Critical?
YES (if skill engine enabled)

## Status
Active, useful

## Problems
- Skill engine and skill implementations use `backend.core.models.*` types while `agent_loop_v2` builds `SkillContext` using `backend.agent` types. The presence of two model namespaces (`backend.core.models` vs `backend.agent.schemas`) is a significant architectural inconsistency that risks silent runtime type/coercion bugs.

## Recommended Action
- MERGE model definitions: choose a canonical model package (prefer `backend.core.models`) and update references or add an adapter layer to translate between the two models consistently.

---

## File Path
backend/agent/agent_loop.py

## Purpose
Legacy agent loop (pre-v2). Maintained alongside v2 for compatibility.

## Used By
Not referenced by codepaths except docs; present in repository.

## Depends On
Same subsystems as v2 but older/leaner.

## Runtime Critical?
NO (legacy)

## Status
Legacy / Dead (no runtime references from server; marked in docs as replaced)

## Problems
- Duplicate codebase surface and confusion for maintainers.

## Recommended Action
- DELETE or ARCHIVE: remove or move to `legacy/` after a short deprecation period and tests pass.

---

### Notes
- There exist many `__pycache__` and re-export modules (`backend/models/*`) that mirror agent types; treat these as convenience shims but document and consolidate models.
