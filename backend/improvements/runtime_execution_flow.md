# Runtime Execution Flow

Describe the full integrated pipeline:

1. observe -> planner -> execute -> capture artifacts
2. validate -> success detection -> website health analysis
3. visual, network, bug detection -> goal completion evaluation
4. persist artifacts -> generate frontend-ready AI report

Services ownership:
- Execution: `backend/services/test_runner.py`
- Orchestration: `backend/services/test_services.py`
- QA Detectors: `backend/agent/services/*`
- Artifact storage: local `artifacts/` mounted at `/artifacts`
