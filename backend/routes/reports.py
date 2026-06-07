from __future__ import annotations

from io import BytesIO
import zipfile
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from backend.database.report_repository import list_reports_for_user, get_report
from backend.services.auth import get_current_user
from backend.services.report_export_service import export_report_to_pdf, list_report_exports


router = APIRouter()


def _pick_first(report: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list)):
            text = str(value).strip()
            if text:
                return text
    return default


def _report_label(report_type: str) -> str:
    return {
        "legacy": "Legacy Report",
        "ai": "AI Report",
        "multi_agent": "Multi-Agent Report",
    }.get(report_type, "Report")


def _map_report(report: Dict[str, Any]) -> Dict[str, Any]:
    report_id = _pick_first(report, "report_id", default=str(report.get("_id") or report.get("test_run_id") or ""))
    report_type = _pick_first(report, "report_type", "type", default="legacy")
    test_name = _pick_first(report, "test_name", "title", "name", default=report_id or "Untitled Report")
    website = _pick_first(report, "website", "url", "target_url", default="")
    generated_date = _pick_first(report, "generated_date", "created_at", "updated_at", default="")
    status = _pick_first(report, "status", "overall_status", default="completed")
    execution_status = _pick_first(report, "execution_status", default=status)
    test_verdict = _pick_first(report, "test_verdict", "overall_status", default="unknown")
    failure_type = _pick_first(report, "failure_type", default="none")
    outcome_label = _pick_first(report, "outcome_label", default="")
    score_raw = report.get("score", report.get("health_score", report.get("website_health_score")))
    try:
        score = None if score_raw is None else float(score_raw)
    except (TypeError, ValueError):
        score = None

    related_test_id = _pick_first(report, "related_test_id", "test_run_id", default=str(report.get("test_run_id") or ""))
    related_bug_id = _pick_first(report, "related_bug_id", "bug_id")
    scenario_tree = report.get("scenario_tree") if isinstance(report.get("scenario_tree"), dict) else None
    risk_summary = report.get("risk_summary") if isinstance(report.get("risk_summary"), dict) else None
    test_type = _pick_first(report, "test_type", "run_type")

    return {
        "report_id": report_id,
        "report_type": report_type if report_type in {"legacy", "ai", "multi_agent"} else "legacy",
        "report_label": report.get("report_label") or _report_label(report_type if report_type in {"legacy", "ai", "multi_agent"} else "legacy"),
        "test_name": test_name,
        "website": website,
        "generated_date": generated_date,
        "status": status,
        "execution_status": execution_status,
        "test_verdict": test_verdict,
        "failure_type": failure_type,
        "outcome_label": outcome_label,
        "score": score,
        "related_test_id": related_test_id or None,
        "related_bug_id": related_bug_id or None,
        "title": _pick_first(report, "title", default=test_name),
        "summary": _pick_first(report, "summary", default=""),
        "test_type": test_type or None,
        "scenario_tree": scenario_tree,
        "risk_summary": risk_summary,
        "objective_coverage": report.get("objective_coverage") if isinstance(report.get("objective_coverage"), list) else None,
    }


def _list_report_docs(current_user_id: str, *, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    docs = list_reports_for_user(current_user_id, limit=limit, skip=skip)
    return [_map_report(doc) for doc in docs]


@router.get("/reports")
def get_reports(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
):
    return {"items": _list_report_docs(current_user["user_id"], limit=limit, skip=skip)}


@router.get("/reports/{report_id}")
def get_report_detail(report_id: str, current_user: dict = Depends(get_current_user)):
    doc = get_report(report_id, user_id=current_user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    return _map_report(doc)


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, current_user: dict = Depends(get_current_user)):
    try:
        export_report_to_pdf(report_id, user_id=current_user["user_id"], include_screenshots=False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    exports = list_report_exports(report_id, user_id=current_user["user_id"])
    export = exports[0] if exports else None
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    file_path = export.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not available")

    filename = f"{export.get('title', 'report')}.pdf"
    return FileResponse(file_path, media_type="application/pdf", filename=filename)


@router.get("/reports/export-all")
def export_all_reports(
    q: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    reports = _list_report_docs(current_user["user_id"], limit=500)
    if q:
        query = q.lower().strip()
        reports = [item for item in reports if query in item["test_name"].lower() or query in item["website"].lower() or query in item["report_type"].lower() or query in item["summary"].lower()]
    if report_type and report_type.lower() != "all":
        normalized_type = report_type.lower().replace(" ", "_").replace("-", "_")
        reports = [item for item in reports if item["report_type"] == normalized_type]
    if status and status.lower() != "all":
        reports = [item for item in reports if item["status"].lower() == status.lower()]

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in reports:
            report_id = item["report_id"]
            try:
                export_report_to_pdf(report_id, user_id=current_user["user_id"], include_screenshots=False)
            except ValueError:
                continue
            exports = list_report_exports(report_id, user_id=current_user["user_id"])
            export = exports[0] if exports else None
            file_path = export.get("file_path") if export else None
            if not file_path:
                continue
            archive.write(file_path, arcname=f"{report_id}.pdf")

    zip_buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="reports-export.zip"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)
