# Frontend Response Structure

The final API entry returns a compact, frontend-ready response and places raw traces under `debug_data`.

Example structure:

{
  "status": "completed",
  "website_health_score": 86,
  "workflow_completion": 0.91,
  "critical_issues": 1,
  "warnings": 4,
  "ai_report": {...},
  "screenshots": [...],
  "coverage": {...},
  "execution_id": "...",
  "execution_time_seconds": ...,
  "debug_data": { ... }
}

Use `ai_report` for detailed sections and keep `debug_data` for developer troubleshooting.
