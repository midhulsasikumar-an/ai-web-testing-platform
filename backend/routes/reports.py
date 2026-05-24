from __future__ import annotations

from io import BytesIO
import zipfile
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from backend.database.report_repository import list_reports_for_user
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
    score_raw = report.get("score", report.get("health_score", report.get("website_health_score")))
    try:
        score = None if score_raw is None else float(score_raw)
    except (TypeError, ValueError):
        score = None

    related_test_id = _pick_first(report, "related_test_id", "test_run_id", default=str(report.get("test_run_id") or ""))
    related_bug_id = _pick_first(report, "related_bug_id", "bug_id")

    return {
        "report_id": report_id,
        "report_type": report_type if report_type in {"legacy", "ai", "multi_agent"} else "legacy",
        "report_label": report.get("report_label") or _report_label(report_type if report_type in {"legacy", "ai", "multi_agent"} else "legacy"),
        "test_name": test_name,
        "website": website,
        "generated_date": generated_date,
        "status": status,
        "score": score,
        "related_test_id": related_test_id or None,
        "related_bug_id": related_bug_id or None,
        "title": _pick_first(report, "title", default=test_name),
        "summary": _pick_first(report, "summary", default=""),
    }


def _list_report_docs(current_user_id: str) -> List[Dict[str, Any]]:
    docs = list_reports_for_user(current_user_id)
    return [_map_report(doc) for doc in docs]


@router.get("/reports")
def get_reports(current_user: dict = Depends(get_current_user)):
    return {"items": _list_report_docs(current_user["user_id"])}


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
    reports = _list_report_docs(current_user["user_id"])
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