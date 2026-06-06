# Autonomous Agent Flow

## End-to-end lifecycle

```text
POST /api/agent/autonomous-test
  -> validate start URL and same-origin policy
  -> create isolated browser context
  -> navigate to start URL
  -> initialize AgentRunState and AgentMemory
  -> loop until done, blocked, or max steps
  -> close browser context
  -> return structured run report
```

## Core loop

```text
observe
  BrowserObserver captures page state, indexed elements, screenshot, viewport,
  console errors, network failures, dialogs, popups, forms, headings, iframes,
  active element, page type, and fingerprint.

think
  PlannerOrchestrator builds PlannerContext from workflow state, page
  classification, form intelligence, auth detection, frontier graph, and
  memory. A specialized planner returns one deterministic AgentAction.

validate
  ActionValidator checks schema intent, confidence, repeated actions,
  repeated failures, target availability, element state, same-origin policy,
  SSRF restrictions, and dangerous action terms.

execute
  ActionExecutor resolves the element through SelectorEngine ranked candidates,
  executes async Playwright actions, captures before/after screenshots,
  waits for page stability, classifies failures, and returns ActionResult.

recover
  RecoveryEngine re-observes, scrolls, escapes modals, retries after stale DOM,
  waits for network idle, refreshes unstable pages, and restarts workflow
  stages when loop prevention triggers.

remember
  AgentMemory stores typed observations, actions, results, selector outcomes,
  navigation frontier, failure patterns, loop signals, and auth hints.

re-observe
  The loop captures a new Observation after each action so the next decision is
  based on actual browser state, not the model's assumption.
```

## Why this resembles real browser agents

Modern browser-control agents do not trust a model to invent selectors or make hidden transitions. They ground the planner in environment state, execute one explicit action, send back the new state, and repeat. This implementation follows that pattern by making the browser harness authoritative for observation, selector choice, execution, recovery, and policy enforcement.

## Loop termination

The loop stops when:

- the model emits `done` and execution succeeds
- a safety policy blocks the run
- repeated pages/actions indicate a loop
- max step budget is reached
- the route or infrastructure cancels the request in a future queue-based runner

## Evidence generated

Each run returns:

- `AgentRunState`
- `AgentStep` timeline
- typed observations
- typed actions
- validations
- action results
- recovery actions
- memory events
- screenshot artifacts
- summary counts
