# AI Web Testing Platform - Complete App Overview

This document explains how the app works, what features it has, and how it is built. It is based on the current repository structure and code paths.

## 1. What This App Is

The app is an AI-assisted web testing platform. A user gives it a target website URL and a testing goal, then the backend uses AI planning plus Playwright browser automation to inspect the site, generate test scenarios, execute browser actions, capture evidence, detect bugs, and produce reports.

At a high level, it is a full-stack product with:

- A Next.js frontend for login, dashboards, test setup, live execution, bugs, reports, and AI chat.
- A FastAPI backend for authentication, test orchestration, browser execution, bug/report generation, AI workspace APIs, and realtime events.
- MongoDB as the main database.
- Playwright as the browser automation engine.
- Groq/OpenAI integrations for AI chat, report narration, and planning support.

## 2. Main User-Facing Features

### Authentication

Users can sign up, log in, refresh sessions, view their profile, and log out.

Relevant code:

- Frontend pages: `frontend/src/app/login`, `frontend/src/app/signup`
- Auth context: `frontend/src/context/auth-context.tsx`
- Frontend API client: `frontend/src/services/auth-api.ts`
- Backend router: `backend/routes/auth_routes.py`
- JWT utilities: `backend/services/jwt_utils.py`
- User storage: MongoDB `users` collection

### Dashboard

The dashboard shows current testing health and activity, including:

- Total tests
- Passed/failed/blocked runs
- Pass rate
- Average health score
- Average duration
- Open bug count
- Recent test runs
- Bug distribution
- AI health/log summaries
- System telemetry widgets

Relevant code:

- Page: `frontend/src/app/dashboard/page.tsx`
- Components: `frontend/src/components/dashboard`
- API service: `frontend/src/services/dashboard-api.ts`
- Backend route: `backend/routes/dashboard.py`

### Run Test

The Run Test screen lets the user configure and launch an AI-assisted test run.

It supports:

- Target URL
- Test name/project metadata
- Natural-language test goal
- AI-generated test plan
- Browser/device/coverage settings
- Live logs while the backend runs
- Step results
- Screenshots and evidence
- Rerun handoff from past tests
- AI copilot panel embedded into the test setup flow

Relevant code:

- Page: `frontend/src/app/run-test/page.tsx`
- Test components: `frontend/src/components/test`
- API service: `frontend/src/services/test-api.ts`
- Backend entrypoint: `POST /api/tests/start` in `backend/server.py`

### Live Execution Streaming

While a test is running, the frontend streams backend progress. The code supports Server-Sent Events and WebSocket-style runtime APIs.

Relevant backend endpoints:

- `GET /api/tests/{test_id}/stream`
- `GET /api/tests/{test_id}/events`
- `GET /api/agent/runs/{run_id}/timeline`
- `WS /api/agent/ws/live-execution`
- `WS /ws/runtime/{execution_id}`
- `WS /api/agent/ws/multi-agent-execution`

Relevant code:

- Frontend stream handling: `frontend/src/services/test-api.ts`
- Frontend run UI: `frontend/src/app/run-test/page.tsx`
- Backend stream routes: `backend/server.py`, `backend/routes/live_execution.py`, `backend/routes/runtime.py`
- Event bus: `backend/events/bus.py`

### Test History

Users can browse previous test runs and inspect an individual run.

It shows:

- Run status
- Target URL
- AI plan details
- Step results
- Logs
- Screenshots
- Bugs found during the run
- Objective coverage
- Rerun actions

Relevant code:

- List page: `frontend/src/app/test-history/page.tsx`
- Detail page: `frontend/src/app/test-history/[id]/page.tsx`
- Backend endpoints: `GET /api/tests`, `GET /api/tests/{test_id}`

### Bug Tracker

The app creates and tracks bugs discovered during test execution.

Bug features include:

- Bug list
- Bug detail view
- Severity and status
- Root cause and evidence
- Screenshots
- Lifecycle tracking
- Status updates
- Fix suggestion generation
- Bug clustering/fingerprints to avoid duplicates

Relevant code:

- List page: `frontend/src/app/bugs/page.tsx`
- Detail page: `frontend/src/app/bugs/[id]/page.tsx`
- Components: `frontend/src/components/bugs`
- Frontend API: `frontend/src/services/bugs-api.ts`
- Backend endpoints: `GET /api/bugs`, `GET /api/bugs/{bug_id}`, `PATCH /api/bugs/{bug_id}/status`
- Bug services: `backend/services/bug_services.py`, `backend/services/bug_lifecycle_service.py`, `backend/services/bug_clustering_service.py`
- MongoDB collections: `bugs`, `bug_lifecycle`

### Reports Center

The reports area collects test and bug reports.

It supports:

- Report list
- Report detail page
- Filtering by report kind/status
- Legacy reports
- AI reports
- Multi-agent reports
- PDF download
- Export-all ZIP
- Report exports and downloads

Relevant code:

- List page: `frontend/src/app/reports/page.tsx`
- Detail page: `frontend/src/app/reports/[id]/page.tsx`
- Frontend API: `frontend/src/services/reports-api.ts`
- Backend routes: `backend/routes/reports.py`, `backend/routes/intelligence.py`
- Report services: `backend/services/ai_report_service.py`, `backend/services/report_library_service.py`, `backend/services/report_export_service.py`
- Report repository: `backend/database/report_repository.py`

### AI Workspace

The AI Workspace is a conversational assistant for understanding test history, reports, bugs, screenshots, and instructions.

It supports:

- Chat sessions
- Streaming chat responses
- User memory
- Report analysis
- Bug analysis
- Screenshot analysis
- Natural-language context resolution
- Test instruction generation
- Sending generated instructions to the Run Test screen
- Recommendations based on prior runs and bugs

Relevant code:

- Page: `frontend/src/app/ai-workspace/page.tsx`
- Components: `frontend/src/components/ai-workspace`
- Frontend API: `frontend/src/services/ai-workspace-api.ts`
- Backend routes: `backend/ai_workspace/routes.py`
- AI workspace service: `backend/ai_workspace/service.py`
- Retrieval: `backend/ai_workspace/retrieval.py`
- Memory/chat persistence: `backend/ai_workspace/memory.py`
- Models: `backend/ai_workspace/models.py`
- MongoDB collections: `ai_chat_sessions`, `ai_chat_messages`, `ai_memory_collection`

### Settings

The settings area includes profile and security screens.

Relevant code:

- Layout: `frontend/src/app/settings/layout.tsx`
- Profile: `frontend/src/app/settings/profile/page.tsx`
- Security: `frontend/src/app/settings/security/page.tsx`
- Components: `frontend/src/components/settings`

## 3. Frontend Architecture

The frontend is built with:

- Next.js 16 App Router
- React 19
- TypeScript
- Tailwind CSS 4
- lucide-react icons
- shadcn/Base UI style primitives
- Local API service modules

Important directories:

- `frontend/src/app` - Next.js routes and pages
- `frontend/src/components` - reusable UI and feature components
- `frontend/src/services` - API clients for backend communication
- `frontend/src/context` - auth and bug contexts
- `frontend/src/lib` - navigation, formatting, local run-state helpers, utilities
- `frontend/src/types` - shared TypeScript interfaces
- `frontend/src/config/api.ts` - resolves the backend API base URL

The frontend expects:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
NEXT_PUBLIC_API_HEALTH_PATH=/health
NEXT_PUBLIC_AUTH_TIMEOUT_MS=10000
```

Auth tokens are stored client-side through the shared HTTP service:

- Access token key: `auth_token`
- Refresh token key: `auth_refresh_token`

The HTTP client automatically attaches auth headers and attempts token refresh when needed.

## 4. Backend Architecture

The backend is built with:

- FastAPI
- Pydantic models
- PyMongo
- Playwright
- JWT authentication
- SlowAPI rate limiting
- Groq/OpenAI AI providers
- ReportLab PDF generation
- BeautifulSoup/requests for discovery-related support

Important directories:

- `backend/server.py` - main FastAPI app, core test endpoints, startup/shutdown, router registration
- `backend/routes` - API routers for auth, dashboard, reports, intelligence, agent runtime, live execution
- `backend/services` - business logic for testing, AI plans, execution, bugs, reports, scoring, auth, safety, watchdogs
- `backend/agent` - autonomous browser agent runtime, planners, skills, memory, validation, world model, recovery
- `backend/multi_agent` - multi-agent test runtime, consensus, shared memory, navigation graph, specialized agents
- `backend/ai_workspace` - chat, memory, retrieval, and AI analysis APIs
- `backend/database` - MongoDB connection and report repository
- `backend/events` - event schemas, event bus, replay engine
- `backend/core/models` - Pydantic models for workflow, actions, observations, reports, memory, validation, auth, intelligence
- `backend/tests` - backend tests and smoke tests

## 5. Main Backend API Surface

### Health and Assets

- `GET /`
- `GET /health`
- `GET /api/health`
- `GET /api/health/deep`
- `GET /screenshots/{file_path}`
- `GET /artifacts/{file_path}`

### Auth

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Tests

- `POST /api/tests/start`
- `POST /api/tests/{test_id}/cancel`
- `GET /api/tests`
- `GET /api/tests/{test_id}`
- `GET /api/tests/{test_id}/stream`
- `GET /api/tests/{test_id}/events`

### Bugs

- `GET /api/bugs`
- `GET /api/bugs/{bug_id}`
- `PATCH /api/bugs/{bug_id}/status`
- `POST /api/bugs/{bug_id}/generate-fix`

### Dashboard

- `GET /api/dashboard/stats`

### Reports

- `GET /api/reports`
- `GET /api/reports/export-all`
- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/download`

### AI Workspace

- `GET /api/ai-workspace/sessions`
- `POST /api/ai-workspace/sessions`
- `GET /api/ai-workspace/sessions/{session_id}`
- `PATCH /api/ai-workspace/sessions/{session_id}`
- `DELETE /api/ai-workspace/sessions/{session_id}`
- `POST /api/ai-workspace/chat`
- `POST /api/ai-workspace/chat/stream`
- `GET /api/ai-workspace/chat/{session_id}/messages`
- `GET /api/ai-workspace/memory`
- `POST /api/ai-workspace/memory`
- `PATCH /api/ai-workspace/memory/{memory_id}`
- `DELETE /api/ai-workspace/memory/{memory_id}`
- `GET /api/ai-workspace/reports/overview`
- `POST /api/ai-workspace/reports/analyze`
- `POST /api/ai-workspace/bugs/analyze`
- `GET /api/ai-workspace/bugs/overview`
- `POST /api/ai-workspace/screenshots/analyze`
- `GET /api/ai-workspace/screenshots/overview`
- `POST /api/ai-workspace/instructions/generate`
- `GET /api/ai-workspace/recommendations`
- `GET /api/ai-workspace/context`
- `GET /api/ai-workspace/resolve/run`
- `GET /api/ai-workspace/resolve/bug`
- `GET /api/ai-workspace/resolve/screenshot`
- `GET /api/ai-workspace/analytics/runs`
- `GET /api/ai-workspace/compare/runs`

### Agent and Multi-Agent Runtime

- `POST /api/agent/autonomous-test`
- `POST /api/agent/multi-agent/run`
- `WS /api/agent/ws/multi-agent-execution`
- `WS /api/agent/ws/live-execution`
- `GET /api/agent/runs/{run_id}/timeline`

### Historical Intelligence

- `GET /api/intelligence/bugs/lifecycle`
- `GET /api/intelligence/bugs/lifecycle/summary`
- `GET /api/intelligence/runs/comparisons`
- `POST /api/intelligence/runs/compare`
- `GET /api/intelligence/runs/{baseline_run_id}/compare/{comparison_run_id}`
- `POST /api/intelligence/reports/{report_id}/export`
- `GET /api/intelligence/reports/{report_id}/exports`
- `GET /api/intelligence/reports/{report_id}/exports/{export_id}/download`

### Simple AI Routes

- `POST /ai/chat`
- `POST /ai/plan`

## 6. How A Test Run Works

### Step 1: User starts a run

The user starts from the Run Test page. The frontend sends a `TestRequest` to:

```http
POST /api/tests/start
```

The request can include:

- `url`
- `test_name`
- `goal`
- `project_name`
- `test_type`
- `ai_plan`
- `browser`
- `device`
- `coverage_level`
- `execution_settings`

### Step 2: Backend creates a test record

`backend/services/test_services.py` creates a MongoDB `test_runs` document with a generated `test_id`, user ownership, status, timestamps, target URL, and run metadata.

### Step 3: Backend chooses execution mode

The backend either:

- Runs an AI-planned test flow when the request has an AI plan or goal.
- Runs the legacy test path for older/simple checks.
- Uses autonomous agent endpoints for autonomous multi-step QA.

The work is scheduled as a background async task from `backend/server.py`.

### Step 4: AI plan generation

The planning layer:

1. Captures a DOM snapshot.
2. Discovers website features, pages, workflows, forms, tables, and actions.
3. Parses user instructions and extracts credentials safely.
4. Detects blocked/security-checkpoint targets.
5. Expands objectives into risk-based scenarios.
6. Caps plans by configured scenario and step limits.
7. Converts the plan into executable `TestCase` and `Step` objects.

Relevant files:

- `backend/services/ai_plan_service.py`
- `backend/services/website_discovery_service.py`
- `backend/services/instruction_parser.py`
- `backend/services/scenario_expansion_service.py`
- `backend/ai/schema/test_plan_schema.py`

### Step 5: Browser execution

The execution engine runs the plan in Playwright.

It handles:

- Browser session startup and cleanup
- Page navigation
- Safe click/fill/wait/hover/select helpers
- Selector resolution
- Recovery candidate generation
- Screenshots per step
- Console and network failure capture
- Step validation
- Continue-on-failure behavior
- Scenario replanning after failures
- Shared state between dependent scenarios

Relevant files:

- `backend/services/execution_service.py`
- `backend/services/test_services.py`
- `backend/agent/browser_session.py`
- `backend/services/selector_resolver.py`
- `backend/services/execution_watchdog.py`
- `backend/services/execution_truth_engine.py`

### Step 6: Realtime progress

As the run executes, progress is written into the test record and streamed to the frontend through SSE/polling endpoints.

The Run Test page listens for events and falls back to polling if streaming fails.

### Step 7: Outcome, bugs, and reports

When execution ends, the backend:

- Applies the truth engine to classify final status.
- Computes execution metrics and health scores.
- Creates bugs from failing results.
- Updates bug lifecycle records.
- Generates AI-readable reports.
- Saves report records.
- Stores screenshots/artifacts.
- Writes a terminal state even if bug/report generation fails.

Relevant files:

- `backend/services/bug_services.py`
- `backend/services/bug_lifecycle_service.py`
- `backend/services/ai_report_service.py`
- `backend/database/report_repository.py`
- `backend/services/scoring`
- `backend/services/run_outcome.py`

## 7. Autonomous Agent System

The `backend/agent` directory contains a more advanced autonomous browser agent.

It includes:

- Agent loop: `agent_loop_v2.py`
- Browser observation: `observer.py`
- Action execution: `executor.py`
- Navigation engine: `navigation.py`
- Memory: `memory_service.py`, `agent/memory`
- Planners: login, exploration, regression
- Skills: authenticate, complete form, dismiss modal, recover navigation, search site, navigate sidebar, detect dashboard
- Safety: action risk and safety policy
- Recovery: recovery engine
- Loop prevention: trajectory/stagnation analysis
- World model: navigation graph, trajectories, graph memory
- Vision: screenshot analysis, visual grounding, visual diff

This system is intended to let the app explore and validate workflows beyond a fixed test script.

## 8. Multi-Agent System

The `backend/multi_agent` runtime coordinates specialized agents.

Agent roles:

- `AuthenticationAgent`
- `NavigationAgent`
- `AccessibilityAgent`
- `PerformanceAgent`
- `VisualQAAgent`

The orchestrator can run agents in parallel, share authentication/browser state, collect findings, build a navigation graph, calculate workflow coverage, run consensus validation, and produce a unified multi-agent report.

Relevant files:

- `backend/multi_agent/orchestrator.py`
- `backend/multi_agent/agents`
- `backend/multi_agent/shared_memory.py`
- `backend/multi_agent/consensus.py`
- `backend/multi_agent/navigation_graph.py`
- `backend/multi_agent/coverage.py`
- `backend/multi_agent/reporting.py`

## 9. Database Design

MongoDB is configured in `backend/database/mongo.py`.

Main collections:

- `test_runs` - test execution records, status, logs, plans, results, screenshots, reports
- `bugs` - bug records generated from failed runs
- `bug_lifecycle` - lifecycle state for recurring/resolved bugs
- `run_comparisons` - comparison records between runs
- `ai_memory_collection` - AI workspace user memory
- `ai_chat_sessions` - AI workspace chat sessions
- `ai_chat_messages` - AI workspace chat messages
- `report_exports` - report export records
- `selector_cache` - cached selectors for browser execution
- `users` - app users
- `revoked_tokens` - logged-out/revoked JWTs with TTL cleanup
- `reports` - AI/report repository records
- `artifacts` - artifact metadata

Indexes are created for user/test lookup, status filtering, recent lists, unique bug IDs/fingerprints, lifecycle lookup, selector cache keys, user emails, and revoked token TTL.

## 10. AI Providers

The backend can use:

- Groq for fast LLM responses and planning/report support.
- OpenAI for AI workspace responses and report support.

Environment variables:

```env
GROQ_API_KEY=
OPENAI_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
OPENAI_MODEL=gpt-4o-mini
```

The AI workspace has fallback behavior when an LLM provider is unavailable, so some analysis can still be generated from retrieved local data.

## 11. Safety, Reliability, and Production Guards

The backend includes several safeguards:

- JWT secret validation
- Optional strict secret checks in production
- CORS allowlist through `FRONTEND_ORIGINS`
- Rate limits for auth endpoints
- Stuck-run cleanup loop
- Execution watchdog
- Browser warmup on startup
- Terminal-state enforcement for completed/failed/cancelled/timed-out runs
- Selector recovery and scenario replanning
- Asset path normalization
- Revoked-token TTL cleanup

Relevant files:

- `backend/services/startup_guards.py`
- `backend/services/rate_limit.py`
- `backend/services/execution_watchdog.py`
- `backend/services/asset_auth.py`
- `backend/agent/safety`

## 12. Local Development

Root `package.json` provides the main scripts:

```bash
npm run install:all
npm run dev
npm run dev:frontend
npm run dev:backend
npm run build
npm run lint
npm run test:backend
```

Local services:

- Frontend: Next.js dev server, usually `http://localhost:3000`
- Backend: Uvicorn FastAPI server at `http://127.0.0.1:8001`
- MongoDB: defaults to `mongodb://localhost:27017` unless `MONGO_URL` is set

Backend `.env` example:

```env
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=ai-web-testing
JWT_SECRET_KEY=replace-with-a-strong-random-secret-at-least-32-chars
FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
GROQ_API_KEY=
OPENAI_API_KEY=
JWT_ALLOW_WEAK_SECRET=
SKIP_BROWSER_WARMUP=
STRICT_SECRETS=
```

Frontend `.env.local` example:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
NEXT_PUBLIC_API_HEALTH_PATH=/health
NEXT_PUBLIC_AUTH_TIMEOUT_MS=10000
```

## 13. Deployment

The backend has a Render deployment file at `render.yaml`.

Render setup:

- Runtime: Python
- Build command installs backend requirements and Playwright Chromium browsers
- Start command runs Uvicorn
- Production env includes strict secrets, frontend origins, Mongo URL, JWT secret, and AI provider keys

The frontend has `frontend/vercel.json`, so it is intended to deploy separately, likely on Vercel, with `NEXT_PUBLIC_API_URL` pointing at the deployed backend.

## 14. Testing

Backend tests live in `backend/tests`.

Covered areas include:

- Execution lifecycle terminal writes
- Watchdog/stuck-run handling
- Continue-on-failure behavior
- Scenario replanning
- Instruction parsing and routing
- Smoke E2E coverage

Run backend tests:

```bash
npm run test:backend
```

Run frontend lint:

```bash
npm run lint
```

## 15. Feature Map By Screen

| Screen | Route | Purpose |
| --- | --- | --- |
| Landing/Login | `/`, `/login` | Entry point and authentication |
| Signup | `/signup` | Create account |
| Dashboard | `/dashboard` | Health, activity, telemetry, recent runs |
| Run Test | `/run-test` | Configure and run AI web tests |
| AI Workspace | `/ai-workspace` | Chat with reports, bugs, screenshots, memory, instructions |
| Test History | `/test-history` | Browse previous runs |
| Test Detail | `/test-history/[id]` | Inspect one run in detail |
| Bugs | `/bugs` | Track discovered issues |
| Bug Detail | `/bugs/[id]` | Inspect issue evidence and remediation |
| Reports | `/reports` | Browse/download generated reports |
| Report Detail | `/reports/[id]` | Detailed report analysis |
| Settings | `/settings/profile`, `/settings/security` | Profile and account security |

## 16. End-To-End Mental Model

Think of the app as a pipeline:

```text
User goal + target URL
  -> frontend sends TestRequest
  -> backend creates test run
  -> AI/discovery creates scenarios
  -> Playwright executes browser steps
  -> progress streams to frontend
  -> screenshots/logs/results are stored
  -> bugs are generated and deduplicated
  -> reports are generated
  -> dashboard/history/reports/AI workspace make the run understandable
```

The important thing is that the app is not just a recorder of tests. It tries to plan, execute, recover, reason about failures, create evidence, and turn raw execution into a bug/report workflow.
