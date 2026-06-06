# Historical Intelligence System

## Purpose
Add a production-style historical layer on top of existing autonomous run reports:
- Bug lifecycle tracking across runs
- Run-to-run comparison
- PDF report export

## Folder Structure
- `backend/core/models/intelligence_models.py`: request and response schemas
- `backend/services/bug_lifecycle_service.py`: fingerprinting, lifecycle status, grouping
- `backend/services/run_comparison_service.py`: run/report comparison engine
- `backend/services/report_export_service.py`: PDF generation and export metadata
- `backend/routes/intelligence.py`: API routes

## Data Model
### Bug lifecycle record
Stored in `db["bug_lifecycle"]` with:
- `fingerprint`
- `status`: `Active`, `Resolved`, `Regressed`, `Flaky`, `Monitoring`
- `occurrences`, `regression_count`, `resolved_count`, `flaky_count`
- `affected_urls`, `affected_components`
- `history` timeline with run/report evidence

### Run comparison record
Stored in `db["run_comparisons"]` with:
- baseline and comparison run/report IDs
- metric deltas
- bug deltas
- screenshot similarity results
- verdict and human-readable summary

### Export record
Stored in `db["report_exports"]` with:
- report ID, export ID, format
- file path, size, title
- comparison metadata

## Lifecycle Flow
1. A run completes and `generate_report()` persists the report.
2. The report generator ingests detected bugs into the lifecycle collection.
3. The lifecycle service fingerprints each bug and either creates or updates the tracked record.
4. Comparison requests load two saved reports and compute deltas.
5. Export requests render a PDF from the saved report and optional comparison result.

## API Routes
- `GET /api/intelligence/bugs/lifecycle`
- `GET /api/intelligence/bugs/lifecycle/summary`
- `GET /api/intelligence/runs/comparisons`
- `POST /api/intelligence/runs/compare`
- `GET /api/intelligence/runs/{baseline_run_id}/compare/{comparison_run_id}`
- `POST /api/intelligence/reports/{report_id}/export`
- `GET /api/intelligence/reports/{report_id}/exports`
- `GET /api/intelligence/reports/{report_id}/exports/{export_id}/download`

## Comparison Logic
- Metric deltas are computed for health, workflow completion, success score, coverage, duration, and issue counts.
- Bug deltas are computed from stable fingerprints derived from title, description, selector, workflow stage, URL, and technical evidence.
- Screenshot comparisons use perceptual hashing to estimate similarity.

## PDF Export Logic
- Generates a branded PDF using `reportlab`.
- Includes summary metrics, bug tables, lifecycle snapshot, and optional embedded screenshots.
- Optionally appends a comparison section for side-by-side regression review.
