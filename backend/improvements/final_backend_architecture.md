# Final Backend Architecture

Overview of the simplified, production-ready backend architecture for the AI testing platform.

- Single runtime execution path: `backend/agent/agent_loop_v2.py`.
- Canonical models: `backend/core/models/*`.
- Eventing: `backend/events/bus.py` (`event_bus`) with JSONL persistence under `artifacts/timeline/{run_id}/events.jsonl`.
- Runtime session manager: `backend/runtime/session_manager.py`.
- Runtime routes: `backend/routes/runtime.py` exposing websocket and control APIs.
- Static artifacts served at `/screenshots` and `/artifacts` via FastAPI mounts.
# Final Backend Architecture

This document describes the canonical runtime architecture for the autonomous AI website testing platform.

- Agent components live under `backend/agent/`.
- Services (detectors, analyzers, orchestrators) are located in `backend/agent/services/`.
- Storage helpers are in `backend/storage/` (S3 integration).
- Execution artifacts and reports are produced by the executor and passed to detectors.

Ownership:
- `website_health_service.py` orchestrates detectors.
- `s3_storage.py` manages screenshot/report artifacts.

Runtime flow:
1. Executor runs scenario and emits artifacts (dom, console, network, screenshots).
2. WebsiteHealthService aggregates detectors and produces the AI report.
3. S3Storage persists screenshots and returns presigned URLs.
4. Event models (`backend/agent/events.py`) can be emitted for live streaming.

Security & production notes:
- Use IAM roles for S3; avoid embedding credentials.
- Ensure long-running tasks are executed in background workers with timeouts.
Dependencies:
- `boto3` (and `botocore`) required for S3 storage. Install in production worker environments.
