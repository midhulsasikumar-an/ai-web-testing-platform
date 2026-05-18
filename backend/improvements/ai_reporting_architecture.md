AI Reporting Architecture

Layers:

- Frontend — dashboard consumes `ai_report` JSON from `/api/agent/autonomous-test`.
- FastAPI route — entrypoint; runs autonomous agent then calls AI reporting pipeline.
- Autonomous Agent Engine — `backend/agent/agent_loop_v2.py` remains the source of truth.
- Execution Analysis — `backend/services/execution_analysis_service.py` performs deterministic analysis.
- AI Report Service — `backend/services/ai_report_service.py` composes the final `AIReadableReport`.
- Optional LLM — `backend/services/report_llm_service.py` performs optional narrative enhancement.
- Persistence — `backend/database/report_repository.py` stores report documents in MongoDB.

The AI reporting layer is post-processing only and does not alter execution. It is designed
for resilience: if the LLM layer is not available, deterministic summarization is used.
