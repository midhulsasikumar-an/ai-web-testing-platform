from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse

from backend.core.models.intelligence_models import ExportRequest, RunComparisonRequest
from backend.services.bug_lifecycle_service import list_bug_lifecycle, summarize_bug_lifecycle
from backend.services.report_export_service import export_report, list_report_exports
from backend.services.run_comparison_service import compare_runs, list_run_comparisons
from backend.services.auth import get_current_user

router = APIRouter()


@router.get("/bugs/lifecycle")
def get_bug_lifecycle(
    status: str | None = Query(default=None),
    website: str | None = Query(default=None),
    workflow_stage: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_bug_lifecycle(user_id=current_user["user_id"], status=status, website=website, workflow_stage=workflow_stage),
        "summary": summarize_bug_lifecycle(current_user["user_id"]),
    }


@router.get("/bugs/lifecycle/summary")
def get_bug_lifecycle_summary(current_user: dict = Depends(get_current_user)):
    return summarize_bug_lifecycle(current_user["user_id"])


@router.get("/runs/comparisons")
def get_run_comparisons(run_id: str | None = Query(default=None), current_user: dict = Depends(get_current_user)):
    return {"items": list_run_comparisons(run_id=run_id, user_id=current_user["user_id"])}


@router.post("/runs/compare")
def post_run_comparison(payload: RunComparisonRequest, current_user: dict = Depends(get_current_user)):
    try:
        return compare_runs(payload.baseline_run_id, payload.comparison_run_id, user_id=current_user["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{baseline_run_id}/compare/{comparison_run_id}")
def get_run_comparison(baseline_run_id: str, comparison_run_id: str, current_user: dict = Depends(get_current_user)):
    try:
        return compare_runs(baseline_run_id, comparison_run_id, user_id=current_user["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reports/{report_id}/export")
def post_report_export(report_id: str, payload: ExportRequest, current_user: dict = Depends(get_current_user)):
    try:
        return export_report(
            report_id,
            format=payload.format,
            user_id=current_user["user_id"],
            include_screenshots=payload.include_screenshots,
            include_comparison=payload.include_comparison,
            comparison_run_id=payload.comparison_run_id,
            title=payload.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports/{report_id}/exports")
def get_report_exports(report_id: str, current_user: dict = Depends(get_current_user)):
    return {"items": list_report_exports(report_id, user_id=current_user["user_id"])}


@router.get("/reports/{report_id}/exports/{export_id}/download")
def download_report_export(report_id: str, export_id: str, current_user: dict = Depends(get_current_user)):
    exports = list_report_exports(report_id, user_id=current_user["user_id"])
    export = next((item for item in exports if item.get("export_id") == export_id), None)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.get("user_id") and export.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    file_path = export.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not available")
    media_type = export.get("media_type") or {
        "pdf": "application/pdf",
        "json": "application/json",
        "markdown": "text/markdown",
        "md": "text/markdown",
        "csv": "text/csv",
    }.get(str(export.get("format") or "pdf").lower(), "application/octet-stream")
    filename = Path(file_path).name if file_path else f"{export.get('title', 'report')}.pdf"
    return FileResponse(file_path, media_type=media_type, filename=filename)
