# Removed Or Replaced Components

## Replaced in the autonomous path

### `backend/agent/agent_loop.py`

Replaced with a typed `AutonomousAgentLoop`. The old loop mixed dict access, Pydantic access, duplicated decision logic, duplicated execution logic, and had invalid function signatures. The new loop orchestrates observer, services, planner, validator, executor, recovery, memory, and workflow state.

### Ambiguous `explore` action

Removed from the canonical action enum. Exploration is now deterministic through `navigate`, `click`, `scroll`, and `back` actions that include selector/element index/reason/confidence when applicable.

### `backend/agent/action_validator.py`

Replaced with `ActionValidator`. The old validator rejected non-dicts and then used attribute access, which made it internally inconsistent. The new validator consumes `AgentAction`, `Observation`, and `AgentMemory`.

### `backend/agent/memory_service.py`

Replaced with layered memory. The old memory stored mostly counts and dicts. The new memory stores observations, actions, results, selector outcomes, navigation frontier, loop signals, failure patterns, discovered pages, successful intents, and auth hints.

### `backend/models/modal_action.py`

Replaced with a compatibility re-export of the canonical `AgentAction` from `backend/agent/schemas.py`.

### `backend/routes/autonomous_agent_route.py`

Replaced with a route that creates an isolated browser session and runs the canonical autonomous loop.

### `backend/server.py` route wiring

Fixed `/api/agent` to mount `autonomous_agent_route.py`. Previously it mounted `routes/autonomous.py` twice, which exposed the static planner route instead of the autonomous agent route.

### `backend/services/safety_service.py`

Replaced with a wrapper over `SafetyPolicy` so legacy domain checks share the stricter navigation policy.

## Still present as legacy compatibility

The following modules remain because frontend or older routes may still depend on them:

- `services/test_runner.py`
- `services/test_cases/*`
- `services/dom_service.py`
- `services/planning_service.py`
- `services/execution_service.py`
- `routes/autonomous.py`
- `routes/ai.py`

They are now considered legacy/static testing infrastructure, not the canonical autonomous agent architecture. A later migration should either wrap them around the new schemas or move them under `backend/legacy/`.

## Duplicate systems identified

- Two observers: `services/dom_service.py` and `services/observer_service.py`
- Two executors: `services/execution_service.py` and `services/action_executor.py`
- Two planning paths: `services/planning_service.py` and `agent/planner.py`
- Two autonomous routes: `routes/autonomous.py` and `routes/autonomous_agent_route.py`
- Mixed sync/async Playwright: `services/test_runner.py` uses sync Playwright while the autonomous agent uses async Playwright

The new production path is `backend/agent/*` plus `/api/agent/autonomous-test`.
