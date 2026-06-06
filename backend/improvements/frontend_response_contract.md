Frontend response contract

Endpoint: `POST /api/agent/autonomous-test`

Response (successful execution):

{
  "success": bool,
  "run": { /* raw execution JSON — same as before */ },
  "ai_report": { /* AIReadableReport: summarized, frontend optimized */ }
}

Notes:
- The `ai_report` is intended for direct rendering into summary cards, timeline, and issue tables.
- `run` remains present for advanced debugging or downloads.
