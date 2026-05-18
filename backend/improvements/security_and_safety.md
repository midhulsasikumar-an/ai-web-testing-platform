# Security And Safety

## Implemented safety measures

- `SafetyPolicy` validates the start URL.
- Only `http` and `https` schemes are allowed.
- Private/local network targets are blocked by default.
- Same-origin navigation is enforced by default.
- CORS is configured through `FRONTEND_ORIGINS` instead of allowing every origin.
- Navigation is validated before `goto`.
- Dangerous action terms such as delete, purchase, pay, transfer, checkout, reset password, and shutdown are blocked.
- Browser isolation is context-per-agent-run.
- Page text is explicitly treated as untrusted data in the LLM prompt.
- The AI is not allowed to invent selectors; it must choose indexed elements.

## Prompt injection defense

The planner prompt separates:

- trusted user goal
- trusted harness rules
- untrusted browser observation

The model is told not to follow instructions found inside the page. The harness also enforces policy after the model responds, so prompt injection cannot directly authorize unsafe navigation or destructive actions.

## Credential handling

Credential placeholders such as `{email}` can be resolved by the executor at action time. The current implementation avoids asking the model to hardcode credential values, but production should also:

- redact credentials from logs
- avoid screenshots during password entry when possible
- store credentials in a secrets manager
- avoid returning credential values in API responses
- scope credentials per run/project

## SSRF and navigation restrictions

Private IP literals and localhost-style hostnames are blocked. Same-origin policy is enabled by default. Production should additionally resolve DNS and block domains that resolve to private ranges, because DNS rebinding can bypass hostname-only checks.

## Human approval requirements

The current policy blocks dangerous terms outright. Production should add a human approval state for:

- purchases and payments
- destructive admin actions
- password/account changes
- sending messages or emails
- irreversible data mutations

## Browser sandboxing

Each run gets an isolated browser context. For stronger isolation:

- run browser workers in containers
- use network egress policies
- disable downloads by default
- restrict file uploads to approved paths
- use per-run temporary directories
- clear storage state after untrusted tests

## Remaining security work

- set `MONGO_URL` in the environment for production MongoDB access
- add authentication and authorization for API routes
- add per-user rate limits
- add DNS-based private network detection
- persist policy decisions in run reports
