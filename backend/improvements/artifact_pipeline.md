# Artifact Pipeline

- Artifacts are stored locally under `artifacts/{execution_id}/`.
- The FastAPI app mounts `/artifacts` to serve files directly during development.
- Each run writes `artifacts.json` with collected metadata and arrays of screenshots.
- Frontend should request images at `/artifacts/{execution_id}/{filename}`.
