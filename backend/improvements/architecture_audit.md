# Autonomous Agent Audit Report

This report is a strict, evidence-based audit of the `backend` in this workspace. All findings are derived from direct code inspection and traced imports/usages.

---

## Overall Architecture Score (0-10)
- Modularity: 6/10 — components are split into logical packages, but model duplication and parallel planning paths reduce coherence.
- Runtime safety: 6/10 — async usage is generally correct; resource lifecycle (Playwright shutdown) and validator bypass create runtime risks.
- AI-agent realism: 7/10 — planners, skill engine, memory, and world-model are implemented and interconnected; however, duplication and model mismatches weaken assurances.
- Scalability: 5/10 — single-process memory and synchronous file operations limit scale without changes.
- Maintainability: 4/10 — duplicated models (`backend.core.models` vs `backend.agent.schemas`) and parallel architectures increase cognitive load and bug risk.
- Production readiness: 4/10 — major gaps (validator bypass, lifecycle hooks, persistence, dependency management) remain.

Final high-level verdict: **Prototype Quality** — core features are implemented and usable, but architectural inconsistencies and several dangerous patterns prevent production deployment without moderate refactoring.

---

## Critical Failures (must fix before production)
1. Validator bypass in recovery: `backend/agent/recovery/recovery_engine.py::recover()` calls `ActionExecutor.execute()` to retry original action without re-running `ActionValidationEngine.validate()` (risk: executing high-risk/low-confidence action without enforcement).
2. Duplicate/Conflicting model namespaces: `backend.core.models.*` and `backend.agent.schemas` define similar enums/models (GoalType, WorkflowState, ActionType, ActionResult, Observation, AgentAction). This produces fragile runtime behaviour and silent coercion risks across the skill engine / orchestrator boundary.
3. Parallel planning flows: two distinct planning architectures exist simultaneously:
   - LLM-driven services pipeline: `backend/services/planning_service.py` + `backend/routes/autonomous.py`
   - Agent skill + legacy planners: `backend/agent/planner/*` + `backend/agent/skill_engine/*` + `agent_loop_v2`
   This duplication increases maintenance cost and is confusing for operators.
4. Missing Playwright lifecycle shutdown: `BrowserSessionManager` is never shut down on application shutdown. `backend/routes/autonomous_agent_route.py` closes contexts but not the global browser handle; `server.py` lacks an app-lifespan shutdown to call `BrowserSessionManager.shutdown()`.
5. In-memory-only memory: `AgentMemory` is ephemeral; there is no persistence adapter or DB integration for multi-run learning or long-term replay.

---

## Fake Architecture / Placeholder Enterprise Code
The repository contains many enterprise-sounding components that are implemented but partially redundant or inconsistent:
- `backend.observability`: Real small implementation — OK (keep).
- `backend.core.models` vs `backend.agent.schemas`: fake duplication — choose canonical models and remove mirrors.
- Several `services/*` modules (planning_service, outcome_validator) are legacy LLM-based wrappers that are not integrated with the v2 agent and should be consolidated or clearly marked legacy.

Recommended actions: MERGE models into `backend.core.models` and update `backend.agent` modules to import canonical models, or provide a strict adapter layer.

---

## Dead Code Report
Files that are present but not used by the runtime server routes or referenced codepaths (candidates for deletion or archival):
- `backend/agent/agent_loop.py` — legacy loop. Not imported by server; docs mention it as replaced.
- `backend/services/planning_service.py` — used only by the legacy `/ai/autonomous/full-test` route; parallel architecture.

Note: There are many re-export shims (`backend/models/*.py`) and `__pycache__` artifacts — these are not harmful but should be cleaned and documented.

---

## Import Problems and Circular Risk
- No immediate import-time failures observed in static inspection, but the codebase uses two model packages that import each other indirectly through different modules which increases the risk of subtle circular imports when refactoring.
- Skill engine imports `backend.core.models.*` while the agent orchestrator builds `SkillContext` using `backend.agent.*` types. Pydantic will sometimes coerce values but this is brittle and constitutes an architectural inconsistency that must be resolved.

---

## Runtime Risks
- Recovery can execute actions without validation (see Critical Failures).
- Browser process lifecycle is not tied to app lifecycle: potential orphaned browsers across deploys/restarts.
- Disk I/O (screenshots) uses synchronous calls inside async functions — small blocking risk under high throughput.
- External LLM client (`groq`) dependency in `services/planning_service.py` requires environment variables and is not mocked; absent keys will cause runtime exceptions if that route is called.

---

## AI-Agent Realism Evaluation
- Strengths:
  - Well-implemented observation subsystem extracting accessibility cues and candidate selectors.
  - Planner implementations (Login, Exploration) are deterministic, goal-aware, and use frontier heuristics.
  - Skill engine, world graph, and trajectory engine are real, non-trivial implementations.
- Weaknesses:
  - Model duplication and namespace mismatch undermine predictability of skill outputs and planner inputs.
  - Memory is only in-run — the system cannot learn across runs without adding persistence adapters.
  - Recovery retries without validator weaken safety and can produce unsafe behaviour.

Conclusion: The system largely behaves like a real autonomous browser agent (not a crawler or random clicker), but architectural inconsistencies and enforcement gaps reduce trust for production autonomous deployments.

---

## Recovery System Evaluation
- Recovery strategies are implemented (dismiss modals, retry selectors, wait, refresh, backtrack).
- Decisioning in `RecoveryEngine.decide()` is concise and appropriate.
- Critical gap: retries performed by `recover()` call the executor directly. Recovery should re-validate or escalate to a planner to avoid repeating unsafe actions.

Recommended action: make recovery produce a new `PlannerDecision` (replan) for risky or repeated failures and only allow safe, validated automatic retries.

---

## Planner Evaluation
- Legacy planners (Login, Exploration, Regression) are deterministic and use observation/form analysis; they are suitable fallbacks.
- Skill engine provides higher-level, LLM-free skills and a registry; skills are grounded and implement concrete logic.
- Problem: Two planning systems (legacy planners vs `services/planning_service`) exist; unify into one path.

---

## Validator Evaluation
- `ActionValidationEngine` covers policy checks, confidence and repeated-failure limits, and element visibility — solid implementation.
- Enforcement gap: nothing stops other code (recovery) from calling executor directly. Make validator central and call executor only through a validated wrapper.

---

## Memory and Loop Prevention Evaluation
- `AgentMemory` provides practical loop-detection heuristics (recent URL repetition, fingerprint frequency, action-key repetition).
- Good: `loop_analyzer` integration and world model produce signals.
- Weakness: all in-memory; lacks persistence or global deduplication for concurrent runs.

Recommended action: add a persistent memory adapter and optionally a run-scoped token to deduplicate across concurrent runs.

---

## Recommended File Actions (KEEP / MERGE / REWRITE / DELETE)
- KEEP: `backend/agent/agent_loop_v2.py`, `backend/agent/executor.py`, `backend/agent/observer.py`, `backend/agent/recovery/recovery_engine.py` (but fix validator bypass), `backend/agent/browser_session.py` (but add shutdown), `backend/agent/selector_engine.py`.
- MERGE: `backend.core.models.*` and `backend.agent.schemas` into one canonical models package (prefer `backend.core.models`).
- MERGE or DEPRECATE: `backend/services/planning_service.py` (LLM pipeline). Either integrate it behind v2 plugin interface or deprecate old route.
- REWRITE: `RecoveryEngine.recover()` to enforce validation and safer retry policies.
- DELETE / ARCHIVE: `backend/agent/agent_loop.py` (legacy) after a short deprecation and test verification.

---

## Actionable Remediation Plan (recommended next steps)
1. Immediately require validator checks before any `executor.execute()` call. Add a single `validated_execute()` wrapper used everywhere (including recovery).
2. Consolidate model definitions: migrate to `backend.core.models` and update `backend.agent` modules (or add adapter layer). Run tests that serialize/deserialize model instances to ensure behaviour parity.
3. Add application lifespan hooks in `server.py` to call `BrowserSessionManager.shutdown()` on shutdown.
4. Decide single planner path: either remove legacy LLM `services/planning_service.py` or adapt it as a plugin. Remove duplicate routes.
5. Add persistence adapter for `AgentMemory` (optional for MVP but required for production telemetry/learning).
6. Harden recovery: re-validate before retry; cap retries; escalate to planner when repeated failures occur.

---

## Final Verdict
- Classification: **Prototype Quality** — the codebase contains many real, well-implemented subsystems (observer, executor, planners, skills, world model). However, architectural inconsistencies (duplicated models and planning paths), a validator bypass, and missing lifecycle/persistence features prevent production readiness.
