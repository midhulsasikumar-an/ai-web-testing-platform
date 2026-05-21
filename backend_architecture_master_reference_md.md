# TestPilot AI — Backend Architecture Master Reference

## Purpose of This Document

This document is the complete backend architecture reference for the TestPilot AI platform.

It explains:

- Backend folder structure
- Purpose of every major file/folder
- API architecture
- Analytics sources
- AI systems
- Workflow systems
- Bug lifecycle systems
- AI Workspace systems
- Frontend-supported capabilities
- Data flow
- Execution flow
- Database collections
- Report systems
- Real-time systems
- Scheduler systems
- AI retrieval systems
- Memory systems

This document is designed so that:

- frontend developers
- backend developers
- AI coding models
- future contributors

can understand the backend completely.

---

# PLATFORM OVERVIEW

TestPilot AI is an AI-first autonomous website testing platform.

The platform combines:

- AI-driven website testing
- autonomous workflows
- semantic navigation
- bug intelligence
- historical analysis
- AI reasoning
- conversational AI
- report generation
- workflow scheduling
- regression tracking
- analytics systems

into one unified AI-native testing operating system.

---

# CORE TECHNOLOGY STACK

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Automation Engine | Playwright |
| Database | MongoDB |
| AI Layer | OpenAI SDK |
| AI Orchestration | LangChain / custom orchestration |
| Scheduling | APScheduler / Celery Beat |
| Realtime Updates | WebSockets / SSE |
| Async Runtime | Async Python |
| Reports | ReportLab / WeasyPrint |
| Image Comparison | Pillow / OpenCV |
| Memory Layer | MongoDB + retrieval system |

---

# COMPLETE BACKEND FOLDER STRUCTURE

```text
backend/
│
├── server.py
├── requirements.txt
├── .env
├── test_ai_workspace.py
│
├── database/
│   ├── mongo.py
│   ├── collections.py
│   └── indexes.py
│
├── models/
│   ├── schema.py
│   ├── workflow_models.py
│   ├── bug_models.py
│   ├── report_models.py
│   ├── analytics_models.py
│   └── ai_models.py
│
├── routes/
│   ├── test_routes.py
│   ├── dashboard.py
│   ├── workflow_routes.py
│   ├── bug_routes.py
│   ├── report_routes.py
│   ├── analytics_routes.py
│   ├── comparison_routes.py
│   └── websocket_routes.py
│
├── services/
│   ├── test_services.py
│   ├── ai_planner.py
│   ├── execution_engine.py
│   ├── analytics_service.py
│   ├── report_service.py
│   ├── screenshot_service.py
│   ├── comparison_service.py
│   ├── workflow_service.py
│   ├── scheduler_service.py
│   ├── bug_service.py
│   ├── bug_lifecycle_service.py
│   ├── recommendation_service.py
│   └── websocket_service.py
│
├── ai_workspace/
│   ├── routes/
│   ├── services/
│   ├── memory/
│   ├── retrieval/
│   ├── prompts/
│   ├── orchestration/
│   ├── models/
│   └── utils/
│
├── workflows/
│   ├── scheduler/
│   ├── executors/
│   ├── parsers/
│   └── monitors/
│
├── reports/
│   ├── pdf/
│   ├── templates/
│   ├── exports/
│   └── generators/
│
├── analytics/
│   ├── stability/
│   ├── coverage/
│   ├── recovery/
│   ├── performance/
│   └── trend_analysis/
│
├── bugs/
│   ├── fingerprinting/
│   ├── lifecycle/
│   ├── comparison/
│   └── visual_diff/
│
├── realtime/
│   ├── sockets/
│   ├── streams/
│   └── event_handlers/
│
├── artifacts/
│   ├── screenshots/
│   ├── reports/
│   ├── logs/
│   ├── videos/
│   └── traces/
│
└── utils/
    ├── helpers.py
    ├── constants.py
    ├── logger.py
    └── validators.py
```

---

# ROOT FILES

# server.py

## Purpose
Main FastAPI application entry point.

## Responsibilities
- initializes FastAPI app
- registers routes
- configures middleware
- initializes database
- initializes websocket systems
- starts scheduler systems
- loads AI workspace

## Frontend Importance
ALL frontend requests begin here.

Frontend pages depend on this file being correctly configured.

---

# requirements.txt

## Purpose
Contains all backend dependencies.

Examples:
- fastapi
- playwright
- pymongo
- openai
- apscheduler
- reportlab
- pillow
- uvicorn

---

# .env

## Purpose
Stores secrets and environment configs.

Contains:
- OPENAI_API_KEY
- MONGO_URI
- DATABASE_NAME
- scheduler configs
- report configs

---

# test_ai_workspace.py

## Purpose
Testing script for AI Workspace system.

## Used For
- testing AI retrieval
- testing memory system
- testing report retrieval
- testing comparisons
- testing workflow generation

---

# DATABASE FOLDER

# database/mongo.py

## Purpose
MongoDB connection initialization.

## Responsibilities
- connect database
- initialize collections
- expose DB instance globally

## Used By
ALL backend services.

---

# database/collections.py

## Purpose
Centralized MongoDB collection references.

## Collections
- test_runs
- workflows
- workflow_runs
- bugs
- bug_history
- reports
- screenshots
- ai_sessions
- ai_messages
- analytics
- execution_logs

---

# database/indexes.py

## Purpose
Creates MongoDB indexes.

## Used For
- faster report retrieval
- faster AI search
- workflow querying
- bug matching
- analytics performance

---

# MODELS FOLDER

Contains all Pydantic schemas and DB models.

---

# models/schema.py

## Purpose
Core test request/response schemas.

## Used For
- run test API
- execution APIs
- frontend payload validation

## Frontend Features Supported
- Run Test page
- execution forms
- AI goal input

---

# models/workflow_models.py

## Purpose
Workflow schemas.

## Contains
- workflow creation model
- schedule model
- workflow execution model

## Frontend Features Supported
- Workflows page
- workflow scheduler UI
- workflow history

---

# models/bug_models.py

## Purpose
Bug schemas.

## Contains
- bug statuses
- bug severity
- recurring bug models
- regression models

## Frontend Features Supported
- Bugs page
- grouped bug history
- recurring issue tracking

---

# models/report_models.py

## Purpose
Report structures.

## Contains
- report summaries
- report metadata
- export models

## Frontend Features Supported
- Detailed Test History page
- PDF download
- AI summaries

---

# models/analytics_models.py

## Purpose
Analytics schemas.

## Contains
- stability scores
- execution metrics
- trend metrics
- recovery metrics

## Frontend Features Supported
- Dashboard analytics
- charts
- stability cards
- trend graphs

---

# models/ai_models.py

## Purpose
AI Workspace schemas.

## Contains
- AI chat models
- memory models
- retrieval models
- recommendation models

## Frontend Features Supported
- AI Workspace page
- AI chat assistant
- AI recommendations

---

# ROUTES FOLDER

Contains all API endpoints.

---

# routes/test_routes.py

## Purpose
Handles AI test execution APIs.

## Main APIs
- POST /run-test
- GET /test-status/{id}
- GET /execution-logs/{id}

## Frontend Features Supported
- Run Test page
- execution monitor
- live logs
- screenshots

---

# routes/dashboard.py

## Purpose
Dashboard analytics APIs.

## Provides
- total tests
- success rates
- stability metrics
- bug metrics
- recent executions

## Frontend Features Supported
- Dashboard cards
- charts
- latest test table
- activity feed

---

# routes/workflow_routes.py

## Purpose
Workflow automation APIs.

## APIs
- create workflow
- update workflow
- pause workflow
- activate workflow
- workflow history

## Frontend Features Supported
- Workflows page
- schedule creation
- workflow monitoring

---

# routes/bug_routes.py

## Purpose
Bug intelligence APIs.

## APIs
- grouped bugs
- recurring bugs
- resolved bugs
- bug evolution

## Frontend Features Supported
- Bugs page
- grouped website bugs
- bug detail page

---

# routes/report_routes.py

## Purpose
Report generation/export APIs.

## APIs
- generate PDF
- download report
- export JSON
- report summary

## Frontend Features Supported
- Detailed Test History
- report downloads
- executive reports

---

# routes/analytics_routes.py

## Purpose
Analytics retrieval APIs.

## APIs
- stability analytics
- coverage analytics
- trend analytics
- performance analytics

## Frontend Features Supported
- Dashboard charts
- AI insight cards
- trend analysis

---

# routes/comparison_routes.py

## Purpose
Run comparison APIs.

## APIs
- compare runs
- compare screenshots
- compare reports
- compare analytics

## Frontend Features Supported
- compare runs feature
- comparison views
- regression analysis

---

# routes/websocket_routes.py

## Purpose
Realtime communication.

## Used For
- live execution logs
- execution updates
- live AI reasoning
- live workflow activity

## Frontend Features Supported
- Run Test live monitor
- live dashboard activity

---

# SERVICES FOLDER

Contains all business logic.

---

# services/test_services.py

## Purpose
Main orchestration service for test execution.

## Responsibilities
- starts AI tests
- initializes Playwright
- triggers planner
- stores reports
- updates analytics

## Frontend Features Supported
- Run Test page
- execution lifecycle

---

# services/ai_planner.py

## Purpose
AI execution planning system.

## Responsibilities
- generate test plans
- AI reasoning
- semantic understanding
- adaptive navigation

## Frontend Features Supported
- AI plan panel
- AI reasoning panel

---

# services/execution_engine.py

## Purpose
Core Playwright execution engine.

## Responsibilities
- browser control
- action execution
- semantic navigation
- retries
- validation

## Frontend Features Supported
- live execution
- action tracking

---

# services/analytics_service.py

## Purpose
Computes platform analytics.

## Generates
- stability scores
- coverage analytics
- success metrics
- recovery metrics
- trend analytics

## Dashboard Data Sources
This service powers:
- Dashboard cards
- charts
- analytics widgets
- AI insight systems

---

# services/report_service.py

## Purpose
AI report generation system.

## Generates
- summaries
- executive reports
- PDF exports
- AI insights

## Frontend Features Supported
- Detailed Test History
- report downloads

---

# services/screenshot_service.py

## Purpose
Screenshot management.

## Responsibilities
- screenshot capture
- screenshot storage
- visual comparisons
- diff generation

## Frontend Features Supported
- screenshot galleries
- visual regression viewer

---

# services/comparison_service.py

## Purpose
Historical comparison engine.

## Compares
- runs
- reports
- screenshots
- analytics
- bugs

## Frontend Features Supported
- compare runs
- regression insights

---

# services/workflow_service.py

## Purpose
Workflow management.

## Responsibilities
- create workflows
- update workflows
- monitor workflows
- workflow execution history

## Frontend Features Supported
- Workflows page
- workflow dashboard

---

# services/scheduler_service.py

## Purpose
Recurring automation engine.

## Responsibilities
- schedule workflows
- recurring execution
- cron handling
- workflow expiration

## Frontend Features Supported
- automated workflows
- recurring testing

---

# services/bug_service.py

## Purpose
Bug storage and retrieval.

## Responsibilities
- save bugs
- group bugs
- fetch bug history

## Frontend Features Supported
- Bugs page
- bug cards
- bug details

---

# services/bug_lifecycle_service.py

## Purpose
Advanced bug intelligence.

## Responsibilities
- recurring issue detection
- resolved issue tracking
- flaky issue tracking
- regression matching

## Frontend Features Supported
- recurring bugs
- resolved labels
- regression indicators

---

# services/recommendation_service.py

## Purpose
AI recommendations.

## Generates
- testing suggestions
- stability warnings
- workflow recommendations
- trend warnings

## Frontend Features Supported
- AI insight cards
- AI Workspace recommendations

---

# services/websocket_service.py

## Purpose
Realtime event broadcasting.

## Broadcasts
- logs
- screenshots
- AI reasoning
- execution progress

## Frontend Features Supported
- live execution updates

---

# AI WORKSPACE FOLDER

This is the conversational AI intelligence layer.

---

# ai_workspace/routes/

Contains AI Workspace APIs.

Examples:
- /ai/chat
- /ai/retrieve-report
- /ai/compare-runs
- /ai/generate-workflow

---

# ai_workspace/services/

Core AI business logic.

Responsibilities:
- AI orchestration
- retrieval
- memory injection
- AI summaries

---

# ai_workspace/memory/

Conversation memory system.

Stores:
- AI sessions
- user context
- active website context
- comparison context

---

# ai_workspace/retrieval/

RAG-style retrieval engine.

Searches:
- reports
- workflows
- bugs
- analytics
- screenshots

---

# ai_workspace/prompts/

Prompt engineering system.

Contains:
- report prompts
- comparison prompts
- workflow prompts
- analytics prompts

---

# ai_workspace/orchestration/

AI execution pipeline.

Flow:

User Query
→ Intent Detection
→ Retrieval
→ Memory Injection
→ Prompt Assembly
→ LLM Response
→ Save Session

---

# WORKFLOWS FOLDER

Contains automation systems.

---

# workflows/scheduler/

Handles recurring workflow scheduling.

---

# workflows/executors/

Executes scheduled tests.

---

# workflows/parsers/

Parses natural language workflows.

Example:
“Run regression every day at 10 PM.”

---

# workflows/monitors/

Tracks workflow health.

---

# REPORTS FOLDER

Contains report generation systems.

---

# reports/pdf/

PDF generation logic.

---

# reports/templates/

Report templates.

---

# reports/exports/

Export systems.

Supports:
- PDF
- JSON
- CSV

---

# ANALYTICS FOLDER

Contains analytics computation systems.

---

# analytics/stability/

Computes stability scores.

Frontend Usage:
- Dashboard stability cards
- trend graphs

---

# analytics/coverage/

Coverage analytics.

Frontend Usage:
- coverage charts
- execution insights

---

# analytics/recovery/

Recovery analytics.

Tracks:
- retries
- recoveries
- fallback success

---

# analytics/performance/

Execution performance metrics.

Tracks:
- duration
- speed
- execution latency

---

# analytics/trend_analysis/

Historical trend intelligence.

Tracks:
- stability trends
- recurring failures
- regression frequency

---

# BUGS FOLDER

Contains advanced bug intelligence systems.

---

# bugs/fingerprinting/

Bug fingerprinting system.

Used for:
- recurring issue matching
- regression tracking

---

# bugs/lifecycle/

Bug lifecycle engine.

Tracks:
- active bugs
- resolved bugs
- flaky bugs

---

# bugs/comparison/

Bug comparison logic.

Compares:
- current run vs previous runs

---

# bugs/visual_diff/

Visual screenshot comparison system.

---

# REALTIME FOLDER

Contains live systems.

---

# realtime/sockets/

WebSocket handlers.

---

# realtime/streams/

Realtime data streams.

---

# realtime/event_handlers/

Handles:
- execution events
- AI events
- workflow events

---

# ARTIFACTS FOLDER

Stores generated files.

---

# artifacts/screenshots/

Stores execution screenshots.

---

# artifacts/reports/

Stores PDFs and exports.

---

# artifacts/logs/

Stores execution logs.

---

# FRONTEND FEATURE → BACKEND MAPPING

# DASHBOARD

## Backend Sources
- analytics_service.py
- dashboard.py
- recommendation_service.py

## Features Supported
- summary cards
- latest test table
- live activity
- stability analytics
- charts
- AI insights

---

# RUN TEST PAGE

## Backend Sources
- test_services.py
- execution_engine.py
- ai_planner.py
- websocket_service.py

## Features Supported
- AI goal execution
- live logs
- screenshots
- AI reasoning
- execution status
- artifacts

---

# AI WORKSPACE

## Backend Sources
- ai_workspace/
- retrieval/
- memory/
- orchestration/

## Features Supported
- conversational AI
- report retrieval
- workflow generation
- comparisons
- recommendations
- bug intelligence

---

# WORKFLOWS PAGE

## Backend Sources
- workflow_service.py
- scheduler_service.py
- workflow_routes.py

## Features Supported
- recurring testing
- workflow scheduling
- automation monitoring
- workflow history

---

# BUGS PAGE

## Backend Sources
- bug_service.py
- bug_lifecycle_service.py
- visual_diff/

## Features Supported
- grouped bugs
- recurring issues
- resolved bugs
- visual regression
- bug evolution

---

# TEST HISTORY PAGE

## Backend Sources
- report_service.py
- comparison_service.py
- analytics_service.py

## Features Supported
- grouped test history
- execution timelines
- historical analytics
- screenshots
- reports

---

# DETAILED TEST HISTORY PAGE

## Backend Sources
- report_service.py
- comparison_service.py
- screenshot_service.py

## Features Supported
- AI summaries
- PDF downloads
- comparisons
- screenshots
- bug evolution
- logs

---

# REALTIME DATA FLOW

```text
Frontend Run Test Page
        ↓
POST /run-test
        ↓
AI Planner
        ↓
Execution Engine
        ↓
Playwright
        ↓
Logs + Screenshots + AI Reasoning
        ↓
WebSocket Events
        ↓
Frontend Live Updates
```

---

# AI WORKSPACE DATA FLOW

```text
User Query
        ↓
AI Workspace Route
        ↓
Intent Detection
        ↓
Retrieval Engine
        ↓
MongoDB Search
        ↓
Memory Injection
        ↓
Prompt Assembly
        ↓
LLM Response
        ↓
Save Conversation
        ↓
Frontend Chat UI
```

---

# WORKFLOW EXECUTION FLOW

```text
Workflow Scheduler
        ↓
Recurring Trigger
        ↓
Workflow Executor
        ↓
AI Test Execution
        ↓
Report Generation
        ↓
Bug Storage
        ↓
Analytics Update
        ↓
Workflow History Update
```

---

# BUG LIFECYCLE FLOW

```text
New Test Run
        ↓
Bug Detection
        ↓
Fingerprint Generation
        ↓
Compare Historical Bugs
        ↓
Determine Status:
- Active
- Resolved
- Regressed
- Flaky
        ↓
Update Bug History
```

---

# ANALYTICS SOURCES

# Stability Score

Generated From:
- failed actions
- recovery rate
- execution consistency
- recurring failures

Used In:
- Dashboard
- reports
- comparisons

---

# Coverage Analytics

Generated From:
- visited pages
- validated elements
- tested flows

Used In:
- Dashboard charts
- reports

---

# Recovery Analytics

Generated From:
- retries
- fallback navigation
- semantic recovery

Used In:
- AI insights
- reports

---

# Bug Analytics

Generated From:
- bug frequency
- recurring issues
- regression patterns

Used In:
- Bugs page
- Dashboard
- AI Workspace

---

# Workflow Analytics

Generated From:
- workflow success rates
- failed executions
- scheduling health

Used In:
- Workflows page
- Dashboard

---

# PRODUCT IDENTITY

TestPilot AI is positioned as:

“An AI-native autonomous testing operating system.”

The backend architecture is designed to support:

- AI execution
- conversational intelligence
- historical reasoning
- workflow automation
- autonomous testing
- intelligent analytics
- regression intelligence
- bug lifecycle tracking
- AI recommendations

in one unified scalable system.

---

# FINAL DEVELOPMENT NOTES

## Backend Status

The backend now supports:

✅ AI-driven testing
✅ AI Workspace intelligence
✅ workflow automation
✅ recurring scheduling
✅ report generation
✅ PDF export
✅ run comparison
✅ bug lifecycle tracking
✅ historical intelligence
✅ conversational retrieval
✅ realtime execution monitoring
✅ advanced analytics

---

# IMPORTANT IMPLEMENTATION PRIORITIES

## Highest Priority
- stable API contracts
- database indexing
- websocket reliability
- workflow scheduler reliability
- AI retrieval optimization

## Medium Priority
- performance optimization
- report beautification
- advanced AI summarization

## Future Expansion
- multi-user workspaces
- collaborative QA systems
- cloud browser grids
- visual heatmaps
- autonomous bug fixing

---

# END OF DOCUMENT

