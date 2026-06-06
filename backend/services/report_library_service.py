from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid
import zipfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.database.mongo import bug_collection, collection


def list_report_library(
    user_id: str,
    *,
    query: Optional[str] = None,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    tests = list(collection.find({"user_id": user_id}, {"_id": 0}))
    bugs = list(bug_collection.find({"user_id": user_id}, {"_id": 0}))

    test_lookup = {str(t.get("test_id")): t for t in tests if t.get("test_id")}
    items: List[Dict[str, Any]] = []

    for test in tests:
        test_id = str(test.get("test_id") or "").strip()
        if not test_id:
            continue

        items.append(
            {
                "report_id": f"test:{test_id}",
                "report_type": "Test Report",
                "test_name": _resolve_test_name(test),
                "website": _extract_website(test.get("target_url") or test.get("url")),
                "generated_date": _as_iso(test.get("created_at")) or datetime.utcnow().isoformat(),
                "status": str(test.get("overall_status") or test.get("status") or "unknown"),
                "score": _coerce_score(test.get("health_score")),
                "related_test_id": test_id,
                "related_bug_id": None,
            }
        )

    for bug in bugs:
        bug_id = str(bug.get("bug_id") or "").strip()
        if not bug_id:
            continue
        linked_test = test_lookup.get(str(bug.get("test_id") or "").strip())

        items.append(
            {
                "report_id": f"bug:{bug_id}",
                "report_type": "Bug Report",
                "test_name": _resolve_test_name(linked_test) if linked_test else _resolve_bug_name(bug),
                "website": _extract_website(bug.get("url")),
                "generated_date": _as_iso(bug.get("created_at")) or datetime.utcnow().isoformat(),
                "status": str(bug.get("status") or "open"),
                "score": _severity_score(str(bug.get("severity") or "medium")),
                "related_test_id": str(bug.get("test_id") or "") or None,
                "related_bug_id": bug_id,
            }
        )

    filtered = _apply_filters(items, query=query, report_type=report_type, status=status)
    return sorted(filtered, key=lambda item: item.get("generated_date", ""), reverse=True)


def export_single_report_pdf(user_id: str, report_id: str) -> Path:
    kind, entity_id = _parse_report_id(report_id)
    payload, meta = _load_entity(user_id, kind, entity_id)

    export_root = Path(__file__).resolve().parents[2] / "artifacts" / "exports" / "library"
    export_root.mkdir(parents=True, exist_ok=True)
    filename = f"{_slugify(meta['title'])}-{uuid.uuid4().hex[:8]}.pdf"
    output_path = export_root / filename

    _build_report_pdf(output_path, payload, meta)
    return output_path


def export_all_reports_zip(
    user_id: str,
    *,
    query: Optional[str] = None,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
) -> Path:
    items = list_report_library(user_id, query=query, report_type=report_type, status=status)
    if not items:
        raise ValueError("No reports available for export")

    export_root = Path(__file__).resolve().parents[2] / "artifacts" / "exports" / "library"
    export_root.mkdir(parents=True, exist_ok=True)

    pdf_paths: List[Path] = []
    for item in items:
        pdf_paths.append(export_single_report_pdf(user_id, str(item.get("report_id"))))

    zip_name = f"reports-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
    zip_path = export_root / zip_name

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in pdf_paths:
            archive.write(path, arcname=path.name)

    return zip_path


def _apply_filters(
    items: List[Dict[str, Any]],
    *,
    query: Optional[str],
    report_type: Optional[str],
    status: Optional[str],
) -> List[Dict[str, Any]]:
    result = items

    if report_type and report_type.lower() != "all":
        wanted = report_type.strip().lower()
        result = [item for item in result if str(item.get("report_type", "")).lower() == wanted]

    if status and status.lower() != "all":
        wanted = status.strip().lower()
        result = [item for item in result if str(item.get("status", "")).lower() == wanted]

    if query:
        q = query.strip().lower()
        result = [
            item
            for item in result
            if q in str(item.get("test_name", "")).lower()
            or q in str(item.get("website", "")).lower()
            or q in str(item.get("report_type", "")).lower()
        ]

    return result


def _build_report_pdf(path: Path, payload: Dict[str, Any], meta: Dict[str, str]) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleLarge", parent=styles["Title"], fontSize=20, leading=24, textColor=colors.HexColor("#0F172A")))

    story: List[Any] = [
        Paragraph(meta["title"], styles["TitleLarge"]),
        Spacer(1, 0.18 * inch),
        Paragraph(f"Type: {meta['type']}", styles["BodyText"]),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["BodyText"]),
        Spacer(1, 0.14 * inch),
    ]

    rows = [["Field", "Value"]]
    for key, value in payload.items():
        rows.append([str(key), _shorten(str(value), 200)])

    table = Table(rows, colWidths=[2.0 * inch, 4.9 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=meta["title"],
        author="AI Testing Platform",
    )
    doc.build(story)


def _load_entity(user_id: str, kind: str, entity_id: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    if kind == "test":
        test = collection.find_one({"user_id": user_id, "test_id": entity_id}, {"_id": 0})
        if not test:
            raise ValueError(f"Test report not found: {entity_id}")
        payload = {
            "Test Name": _resolve_test_name(test),
            "Website": _extract_website(test.get("target_url") or test.get("url")),
            "Status": str(test.get("overall_status") or test.get("status") or "unknown"),
            "Score": _coerce_score(test.get("health_score")) or 0,
            "Run Type": str(test.get("run_type") or test.get("test_type") or "AI Generated Test"),
            "Created At": _as_iso(test.get("created_at")) or "",
            "Goal": str(test.get("goal") or ""),
            "Summary": str(test.get("ai_summary") or test.get("report") or ""),
        }
        meta = {"title": f"{payload['Test Name']} - Test Report", "type": "Test Report"}
        return payload, meta

    if kind == "bug":
        bug = bug_collection.find_one({"user_id": user_id, "bug_id": entity_id}, {"_id": 0})
        if not bug:
            raise ValueError(f"Bug report not found: {entity_id}")
        payload = {
            "Bug Name": _resolve_bug_name(bug),
            "Description": str(bug.get("bug_description") or bug.get("description") or ""),
            "Severity": str(bug.get("severity") or "medium"),
            "Status": str(bug.get("status") or "open"),
            "Website": _extract_website(bug.get("url")),
            "Created At": _as_iso(bug.get("created_at")) or "",
            "Linked Test": str(bug.get("test_name") or bug.get("test_id") or ""),
        }
        meta = {"title": f"{payload['Bug Name']} - Bug Report", "type": "Bug Report"}
        return payload, meta

    raise ValueError(f"Unsupported report type: {kind}")


def _parse_report_id(report_id: str) -> Tuple[str, str]:
    parts = str(report_id).split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid report id: {report_id}")
    return parts[0], parts[1]


def _resolve_test_name(test: Optional[Dict[str, Any]]) -> str:
    if not test:
        return "Unnamed Test"

    candidates = [
        test.get("test_name"),
        test.get("project"),
        test.get("goal"),
        (test.get("ai_plan") or {}).get("instruction") if isinstance(test.get("ai_plan"), dict) else None,
        _extract_website(test.get("target_url") or test.get("url")),
        test.get("test_id"),
    ]
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return _shorten(value, 90)
    return "Unnamed Test"


def _resolve_bug_name(bug: Dict[str, Any]) -> str:
    name = str(bug.get("bug_name") or bug.get("title") or "").strip()
    if name:
        return _shorten(name, 50)
    description = str(bug.get("bug_description") or bug.get("description") or "").strip()
    return _shorten(description or "Detected bug", 50)


def _extract_website(raw_url: Any) -> str:
    value = str(raw_url or "").strip()
    if not value:
        return "unknown"

    normalized = value
    if "//" not in normalized:
        normalized = f"https://{normalized}"

    try:
        host = normalized.split("//", 1)[1].split("/", 1)[0].strip().lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return value


def _as_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value or "").strip()
    return text


def _coerce_score(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _severity_score(severity: str) -> int:
    mapping = {
        "critical": 25,
        "high": 45,
        "medium": 65,
        "low": 85,
    }
    return mapping.get(severity.lower(), 60)


def _shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _slugify(value: str) -> str:
    cleaned = [char.lower() if char.isalnum() else "-" for char in value]
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "report"
