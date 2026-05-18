# Architecture Refactor

## Why this refactor was required

The previous backend had three overlapping execution systems:

- legacy synchronous Playwright checks in `services/test_runner.py`
- static LLM test-plan generation in `routes/autonomous.py`
- an autonomous agent loop in `agent/agent_loop.py`

Those systems used different action names, mixed dicts and Pydantic models, duplicated DOM observation, duplicated execution, and routed the wrong autonomous router from `server.py`. The autonomous loop could fail before execution because AI actions were parsed as dicts but consumed as models.

## New canonical autonomous architecture

The autonomous path is now centered on `backend/agent/`:

- `schemas.py`: single source of truth for `AgentAction`, `Observation`, `ObservedElement`, `ActionResult`, `ValidationResult`, `MemoryEvent`, `AgentRunState`, `AgentStep`, and `BrowserArtifact`.
- `observer.py`: production observer that emits indexed elements, selector candidates, page metadata, screenshot artifacts, console/network signals, viewport state, iframe URLs, and page fingerprints.
- `planner/`: deterministic goal-driven planners. `LoginPlanner`, `ExplorationPlanner`, and `RegressionPlanner` produce explicit actions from workflow state, page classification, form analysis, auth signals, frontier state, and memory.
- `action_validator.py`: typed validation with safety policy, repeated-action protection, target checks, editable checks, and exploration checks.
- `executor.py`: robust async Playwright execution with selector ranking, retries, navigation handling, screenshots, typed results, and failure classification.
- `recovery.py`: adaptive recovery for stale selectors, timeouts, modal blocks, and navigation failures.
- `memory_service.py`: layered run memory for observations, actions, failures, selectors, navigation frontier, loops, discovered pages, and auth state.
- `services/frontier_service.py`: graph-driven exploration frontier using URL novelty, depth, goal terms, semantic labels, and safety policy.
- `services/form_service.py`: form intelligence for field classification, submit detection, and confidence scoring.
- `services/auth_detector.py`: authentication detection using URL/content/cookie/logout/profile signals.
- `services/page_classifier.py`: dynamic page classification for login, dashboard, settings, forms, landing, modal, and error pages.
- `services/observation_diff.py`: state differencing for URL, fingerprint, element, modal, and error changes.
- `browser_session.py`: isolated context-per-run browser session manager with reusable browser process and signal capture.
- `safety.py`: domain policy, private-host blocking, same-origin restrictions, dangerous action blocking, and navigation validation.
- `outcome.py`: structured expected-outcome validation.

## Old vs new flow

Old autonomous flow:

```text
observe dict
ask model for loose JSON
sometimes treat JSON as dict
sometimes treat JSON as Pydantic
resolve target text to selector
force click/fill
substring outcome check
append dict memory
```

New autonomous flow:

```text
BrowserSessionManager creates isolated context
BrowserObserver captures typed Observation
PageClassifier, FormService, AuthDetector, FrontierService enrich state
PlannerOrchestrator chooses a deterministic AgentAction
ActionValidator checks contract and policy
ActionExecutor executes through ranked selectors
OutcomeValidator validates expected outcome
RecoveryEngine repairs or replans after failure
AgentMemory records typed state and loop signals
AgentRunState returns structured report
```

The ambiguous `explore` action was removed. Exploration is now represented by deterministic `navigate`, `click`, `scroll`, or `back` actions, each with selector/element index/reason/confidence when applicable.

## Merged/replaced responsibilities

- `models/modal_action.py` now re-exports the canonical `AgentAction`.
- `routes/autonomous_agent_route.py` now runs the canonical autonomous loop directly.
- `server.py` now mounts the actual autonomous agent router under `/api/agent`.
- `services/safety_service.py` delegates domain checks to the new `SafetyPolicy`.

Legacy static testing endpoints are intentionally left in place for compatibility, but the autonomous agent path no longer depends on their weak dict contracts.

## AI communication flow

The model no longer receives raw selectors as the primary interface. It receives a compact typed observation:

- URL and title
- page type
- trusted harness metadata
- untrusted page text excerpt
- indexed elements with role, tag, label, visibility, enabled/editable state
- recent memory and frontier state

The model is instructed to return only one typed action and to prefer `element_index`. The harness owns selectors and execution.

## Browser lifecycle flow

`BrowserSessionManager` keeps a reusable browser process and creates an isolated context for each agent run. Each context owns its page, console/network/dialog/popup signals, cookies, storage, and cleanup lifecycle. This resembles production browser-agent platforms where isolation is per task but the browser process can be pooled.
