from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.core.models.intelligence_models import ExportRequest, RunComparisonRequest
from backend.services.bug_lifecycle_service import list_bug_lifecycle, summarize_bug_lifecycle
from backend.services.report_export_service import export_report_to_pdf, list_report_exports
from backend.services.run_comparison_service import compare_runs, list_run_comparisons

router = APIRouter()


@router.get("/bugs/lifecycle")
def get_bug_lifecycle(
    status: str | None = Query(default=None),
    website: str | None = Query(default=None),
    workflow_stage: str | None = Query(default=None),
):
    return {
        "items": list_bug_lifecycle(status=status, website=website, workflow_stage=workflow_stage),
        "summary": summarize_bug_lifecycle(),
    }


@router.get("/bugs/lifecycle/summary")
def get_bug_lifecycle_summary():
    return summarize_bug_lifecycle()


@router.get("/runs/comparisons")
def get_run_comparisons(run_id: str | None = Query(default=None)):
    return {"items": list_run_comparisons(run_id=run_id)}


@router.post("/runs/compare")
def post_run_comparison(payload: RunComparisonRequest):
    try:
        return compare_runs(payload.baseline_run_id, payload.comparison_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{baseline_run_id}/compare/{comparison_run_id}")
def get_run_comparison(baseline_run_id: str, comparison_run_id: str):
    try:
        return compare_runs(baseline_run_id, comparison_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reports/{report_id}/export")
def post_report_export(report_id: str, payload: ExportRequest):
    if payload.format.lower() != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF export is supported")
    try:
        return export_report_to_pdf(
            report_id,
            include_screenshots=payload.include_screenshots,
            include_comparison=payload.include_comparison,
            comparison_run_id=payload.comparison_run_id,
            title=payload.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports/{report_id}/exports")
def get_report_exports(report_id: str):
    return {"items": list_report_exports(report_id)}


@router.get("/reports/{report_id}/exports/{export_id}/download")
def download_report_export(report_id: str, export_id: str):
    exports = list_report_exports(report_id)
    export = next((item for item in exports if item.get("export_id") == export_id), None)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    file_path = export.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not available")
    return FileResponse(file_path, media_type="application/pdf", filename=f"{export.get('title', 'report')}.pdf")
