from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.database.mongo import collection as test_runs_collection
from backend.database.mongo import db


REPORT_COLLECTION = db["reports"]

try:
    REPORT_COLLECTION.create_index("report_key", unique=True)
    REPORT_COLLECTION.create_index([("user_id", 1), ("created_at", -1)])
except Exception:
    pass


def save_report(
    report: Dict[str, Any],
    *,
    report_type: Optional[str] = None,
    user_id: Optional[str] = None,
    test_run_id: Optional[str] = None,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    payload = normalize_report_document(
        report,
        report_type=report_type,
        user_id=user_id,
        test_run_id=test_run_id,
        title=title,
        summary=summary,
        status=status,
    )

    existing = REPORT_COLLECTION.find_one({"report_key": payload["report_key"]}, {"_id": 0, "report_id": 1, "created_at": 1})
    if existing:
        payload["report_id"] = str(existing.get("report_id") or payload["report_id"])
        payload["created_at"] = existing.get("created_at") or payload["created_at"]

    REPORT_COLLECTION.replace_one({"report_key": payload["report_key"]}, payload, upsert=True)
    return str(payload["report_id"])


def get_report(report_id: str, user_id: Optional[str] = None) -> Dict[str, Any] | None:
    query: Dict[str, Any] = {"report_id": str(report_id)}
    if user_id:
        query["user_id"] = user_id
    report = REPORT_COLLECTION.find_one(query, {"_id": 0})
    if report:
        return report

    query = {"test_run_id": str(report_id)}
    if user_id:
        query["user_id"] = user_id
    report = REPORT_COLLECTION.find_one(query, {"_id": 0})
    if report:
        return report

    return None


def list_reports_for_user(
    user_id: str,
    *,
    query: Optional[str] = None,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filters: Dict[str, Any] = {"user_id": user_id}
    if report_type and report_type.lower() != "all":
        filters["report_type"] = _normalize_report_type(report_type)
    if status and status.lower() != "all":
        filters["status"] = status

    reports = list(REPORT_COLLECTION.find(filters, {"_id": 0}))
    if query:
        q = query.strip().lower()
        reports = [
            item
            for item in reports
            if q in str(item.get("title", "")).lower()
            or q in str(item.get("summary", "")).lower()
            or q in str(item.get("website", "")).lower()
            or q in str(item.get("report_type", "")).lower()
            or q in str(item.get("test_run_id", "")).lower()
        ]

    return sorted(reports, key=_sort_key, reverse=True)


def migrate_reports_from_test_runs(*, user_id: Optional[str] = None) -> Dict[str, int]:
    query: Dict[str, Any] = {
        "$or": [
            {"report": {"$exists": True, "$ne": None}},
            {"ai_report": {"$exists": True, "$ne": None}},
            {"ai_summary": {"$exists": True, "$ne": None}},
            {"summary": {"$exists": True, "$ne": None}},
        ]
    }
    if user_id:
        query["user_id"] = user_id

    migrated = 0
    skipped = 0

    for test_run in test_runs_collection.find(query, {"_id": 0}):
        if not _has_report_content(test_run):
            skipped += 1
            continue
        report_id = save_report(
            test_run,
            report_type="legacy",
            user_id=str(test_run.get("user_id") or user_id or ""),
            test_run_id=str(test_run.get("test_id") or test_run.get("execution_id") or ""),
            title=_legacy_title(test_run),
            summary=_legacy_summary(test_run),
            status=str(test_run.get("status") or "completed"),
        )
        if report_id:
            migrated += 1

    return {"migrated": migrated, "skipped": skipped}


def normalize_report_document(
    report: Dict[str, Any],
    *,
    report_type: Optional[str] = None,
    user_id: Optional[str] = None,
    test_run_id: Optional[str] = None,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    payload = dict(report or {})
    payload.pop("_id", None)

    resolved_type = _normalize_report_type(report_type or payload.get("report_type") or payload.get("type"))
    resolved_user_id = str(
        user_id
        or payload.get("user_id")
        or payload.get("created_by")
        or payload.get("owner_id")
        or (payload.get("debug_data", {}) if isinstance(payload.get("debug_data"), dict) else {}).get("user_id")
        or ""
    ).strip()
    resolved_test_run_id = str(
        test_run_id
        or payload.get("test_run_id")
        or payload.get("execution_id")
        or payload.get("run_id")
        or (payload.get("debug_data", {}) if isinstance(payload.get("debug_data"), dict) else {}).get("run_id")
        or payload.get("report_id")
        or ""
    ).strip()

    created_at = _normalize_timestamp(payload.get("created_at") or payload.get("generated_date") or datetime.utcnow())
    resolved_title = _derive_title(payload, resolved_type, title, resolved_test_run_id)
    resolved_summary = _derive_summary(payload, resolved_type, summary)
    resolved_status = str(status or payload.get("status") or "completed").strip() or "completed"

    payload["report_id"] = str(payload.get("report_id") or uuid.uuid4())
    payload["user_id"] = resolved_user_id
    payload["test_run_id"] = resolved_test_run_id
    payload["report_type"] = resolved_type
    payload["title"] = resolved_title
    payload["summary"] = resolved_summary
    payload["status"] = resolved_status
    payload["created_at"] = created_at
    payload["generated_date"] = str(payload.get("generated_date") or created_at)
    payload["test_name"] = str(payload.get("test_name") or resolved_title).strip() or resolved_title
    payload["website"] = str(
        payload.get("website")
        or payload.get("url")
        or payload.get("target_url")
        or (payload.get("debug_data", {}) if isinstance(payload.get("debug_data"), dict) else {}).get("url")
        or ""
    ).strip()
    payload["score"] = _derive_score(payload)
    payload["related_test_id"] = _derive_related_test_id(payload, resolved_type, resolved_test_run_id)
    payload["related_bug_id"] = _first_text(payload, "related_bug_id", "bug_id") or None
    payload["report_key"] = f"{resolved_user_id}:{resolved_test_run_id}:{resolved_type}"
    payload.setdefault("report_label", _report_label(resolved_type))
    payload.setdefault("source_collection", payload.get("source_collection") or "reports")
    return payload


def _has_report_content(test_run: Dict[str, Any]) -> bool:
    return any(
        value not in (None, "", [], {})
        for value in (
            test_run.get("report"),
            test_run.get("ai_report"),
            test_run.get("ai_summary"),
            test_run.get("summary"),
        )
    )


def _legacy_title(test_run: Dict[str, Any]) -> str:
    candidates = [
        test_run.get("project"),
        test_run.get("test_name"),
        test_run.get("goal"),
        test_run.get("url"),
        test_run.get("test_id"),
    ]
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return "Legacy Report"


def _legacy_summary(test_run: Dict[str, Any]) -> str:
    candidates = [
        test_run.get("ai_summary"),
        test_run.get("report"),
        test_run.get("summary"),
    ]
    for candidate in candidates:
        text = _to_text(candidate)
        if text:
            return text
    return "Legacy test execution report."


def _normalize_report_type(value: Optional[str]) -> str:
    normalized = str(value or "legacy").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in {"legacy", "test_report", "bug_report"}:
        return "legacy"
    if normalized in {"ai", "ai_report", "ai_report_summary"}:
        return "ai"
    if normalized in {"multi_agent", "multiagent", "multi_agent_report"}:
        return "multi_agent"
    return normalized or "legacy"


def _derive_title(report: Dict[str, Any], report_type: str, explicit_title: Optional[str], test_run_id: str) -> str:
    if explicit_title and explicit_title.strip():
        return explicit_title.strip()

    candidates: List[Any] = []
    if report_type == "legacy":
        candidates.extend([report.get("test_name"), report.get("project"), report.get("goal"), report.get("url")])
    elif report_type == "ai":
        ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
        candidates.extend([ai_report.get("executive_summary"), ai_report.get("interaction_narrative"), report.get("goal"), report.get("url")])
    elif report_type == "multi_agent":
        consensus = report.get("consensus", {}) if isinstance(report.get("consensus"), dict) else {}
        candidates.extend([report.get("title"), report.get("goal"), consensus.get("summary")])

    candidates.extend([report.get("title"), report.get("name"), test_run_id])
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value

    return {
        "legacy": "Legacy Report",
        "ai": "AI Report",
        "multi_agent": "Multi-Agent Report",
    }.get(report_type, "Report")


def _derive_summary(report: Dict[str, Any], report_type: str, explicit_summary: Optional[str]) -> str:
    if explicit_summary and explicit_summary.strip():
        return explicit_summary.strip()

    candidates: List[Any] = []
    if report_type == "legacy":
        candidates.extend([report.get("ai_summary"), report.get("report"), report.get("summary")])
    elif report_type == "ai":
        ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
        report_core = ai_report.get("report_core", {}) if isinstance(ai_report.get("report_core"), dict) else {}
        candidates.extend([ai_report.get("executive_summary"), ai_report.get("interaction_narrative"), report_core.get("narrative"), report.get("summary")])
    elif report_type == "multi_agent":
        consensus = report.get("consensus", {}) if isinstance(report.get("consensus"), dict) else {}
        candidates.extend([consensus.get("summary"), report.get("summary"), report.get("goal")])

    candidates.extend([report.get("ai_summary"), report.get("report"), report.get("goal"), report.get("status")])
    for candidate in candidates:
        text = _to_text(candidate)
        if text:
            return text

    return "Report generated successfully."


def _derive_score(report: Dict[str, Any]) -> Optional[float]:
    for key in ("score", "health_score", "website_health_score"):
        value = report.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _derive_related_test_id(report: Dict[str, Any], report_type: str, test_run_id: str) -> Optional[str]:
    if report_type == "legacy" and test_run_id:
        return test_run_id
    value = _first_text(report, "related_test_id")
    return value or None


def _first_text(report: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list)):
            text = str(value).strip()
            if text:
                return text
    return ""


def _report_label(report_type: str) -> str:
    return {
        "legacy": "Legacy Report",
        "ai": "AI Report",
        "multi_agent": "Multi-Agent Report",
    }.get(report_type, "Report")


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return str(value).strip()
    return str(value).strip()


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _sort_key(report: Dict[str, Any]) -> str:
    for key in ("generated_date", "created_at", "updated_at"):
        value = report.get(key)
        if value:
            return str(value)
    return ""
