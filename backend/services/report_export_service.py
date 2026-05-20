from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi.encoders import jsonable_encoder
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.database.mongo import db, report_export_collection
from backend.services.bug_lifecycle_service import summarize_bug_lifecycle, _resolve_path
from backend.services.run_comparison_service import compare_runs

REPORT_COLLECTION = db["reports"]


def export_report_to_pdf(
    report_id: str,
    *,
    user_id: Optional[str] = None,
    include_screenshots: bool = True,
    include_comparison: bool = False,
    comparison_run_id: Optional[str] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    report = _load_report(report_id, user_id=user_id)
    comparison = None
    if include_comparison and comparison_run_id:
        comparison = compare_runs(_report_run_id(report, report_id), comparison_run_id, user_id=user_id, persist=False)

    export_id = str(uuid.uuid4())
    export_title = title or f"Report {report.get('report_id') or report_id}"
    export_root = Path(__file__).resolve().parents[2] / "artifacts" / "exports" / (report.get("report_id") or report_id)
    export_root.mkdir(parents=True, exist_ok=True)
    pdf_path = export_root / f"{_slugify(export_title)}.pdf"

    _build_pdf(pdf_path, report, title=export_title, include_screenshots=include_screenshots, comparison=comparison)

    record = {
        "export_id": export_id,
        "report_id": report.get("report_id") or report_id,
        "user_id": user_id or report.get("user_id") or "",
        "format": "pdf",
        "file_path": str(pdf_path),
        "title": export_title,
        "include_screenshots": include_screenshots,
        "include_comparison": include_comparison,
        "comparison_run_id": comparison_run_id,
        "file_size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
        "created_at": datetime.utcnow(),
    }
    report_export_collection.insert_one(jsonable_encoder(record))
    record["download_url"] = f"/api/intelligence/reports/{record['report_id']}/exports/{export_id}/download"
    return record


def list_report_exports(report_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"report_id": report_id}
    if user_id:
        query["user_id"] = user_id
    return list(report_export_collection.find(query, {"_id": 0}).sort("created_at", -1))


def _build_pdf(path: Path, report: Dict[str, Any], *, title: str, include_screenshots: bool, comparison: Optional[Dict[str, Any]]) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontSize=22, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#0F172A")))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], fontSize=14, leading=18, textColor=colors.HexColor("#1D4ED8"), spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name="BodyTextSmall", parent=styles["BodyText"], fontSize=9.5, leading=12, spaceAfter=4))
    styles.add(ParagraphStyle(name="MetaText", parent=styles["BodyText"], fontSize=9, leading=11, textColor=colors.HexColor("#334155")))

    story: List[Any] = []
    story.append(Paragraph(title, styles["ReportTitle"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Report ID: {report.get('report_id', '')}", styles["MetaText"]))
    story.append(Paragraph(f"Run ID: {_report_run_id(report, '')}", styles["MetaText"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["MetaText"]))
    story.append(Spacer(1, 0.15 * inch))

    story.extend(_build_summary_table(report, styles))
    story.append(Spacer(1, 0.12 * inch))

    narrative = _extract_narrative(report)
    if narrative:
        story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
        story.append(Paragraph(_escape(narrative), styles["BodyTextSmall"]))

    story.append(Paragraph("Key Metrics", styles["SectionHeading"]))
    story.extend(_metric_paragraphs(report, styles))

    lifecycle = summarize_bug_lifecycle(report.get("user_id"))
    story.append(Paragraph("Bug Lifecycle Snapshot", styles["SectionHeading"]))
    story.extend(_lifecycle_paragraphs(lifecycle, styles))

    story.append(Paragraph("Detected Bugs", styles["SectionHeading"]))
    story.extend(_bug_table(report, styles))

    if include_screenshots:
        screenshots = _extract_screenshots(report)
        if screenshots:
            story.append(Paragraph("Screenshots", styles["SectionHeading"]))
            story.extend(_image_gallery(screenshots, styles))

    if comparison:
        story.append(PageBreak())
        story.append(Paragraph("Run Comparison", styles["SectionHeading"]))
        story.extend(_comparison_paragraphs(comparison, styles))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=title,
        author="AI Testing Platform",
    )
    doc.build(story, onFirstPage=_page_decorator, onLaterPages=_page_decorator)


def _build_summary_table(report: Dict[str, Any], styles) -> List[Any]:
    metrics = report.get("execution_summary", {}) if isinstance(report.get("execution_summary"), dict) else {}
    rows = [
        ["Website Health", f"{report.get('website_health_score', 0)} / 100"],
        ["Workflow Completion", f"{float(report.get('workflow_completion', 0.0) or 0.0):.2%}"],
        ["Success Rate", f"{float(metrics.get('success_rate', 0.0) or 0.0):.2%}"],
        ["Pages Visited", str(metrics.get("pages_visited", 0))],
        ["Actions Executed", str(metrics.get("actions_executed", 0))],
        ["Duration", f"{float(metrics.get('duration_seconds', 0.0) or 0.0):.1f}s"],
    ]
    table = Table(rows, colWidths=[2.1 * inch, 3.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2FE")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [table, Spacer(1, 0.12 * inch)]


def _metric_paragraphs(report: Dict[str, Any], styles) -> List[Any]:
    ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
    success_scoring = ai_report.get("success_scoring", {}) if isinstance(ai_report.get("success_scoring"), dict) else {}
    coverage = report.get("coverage", {}) if isinstance(report.get("coverage"), dict) else {}
    lines = [
        f"Critical issues: {int(report.get('critical_issues', 0) or 0)}",
        f"High issues: {int(report.get('high_issues', 0) or 0)}",
        f"Medium issues: {int(report.get('medium_issues', 0) or 0)}",
        f"Low issues: {int(report.get('low_issues', 0) or 0)}",
        f"Coverage score: {coverage.get('coverage_score', 0)}",
        f"Success score: {float(success_scoring.get('overall_score', 0.0) or 0.0):.2f}",
    ]
    return [Paragraph(_escape(line), styles["BodyTextSmall"]) for line in lines]


def _lifecycle_paragraphs(lifecycle: Dict[str, Any], styles) -> List[Any]:
    lines = [
        f"Total tracked bugs: {lifecycle.get('total_bugs', 0)}",
        f"Recurring bugs: {lifecycle.get('recurring_bugs', 0)}",
        f"Regressed bugs: {lifecycle.get('regressed_bugs', 0)}",
        f"Status breakdown: {lifecycle.get('by_status', {})}",
    ]
    return [Paragraph(_escape(line), styles["BodyTextSmall"]) for line in lines]


def _bug_table(report: Dict[str, Any], styles) -> List[Any]:
    bugs = _extract_bugs(report)[:12]
    if not bugs:
        return [Paragraph("No bugs were detected in this report.", styles["BodyTextSmall"])]

    rows = [["Severity", "Title", "Workflow", "Evidence"]]
    for bug in bugs:
        evidence = bug.get("description") or bug.get("technical_explanation") or bug.get("issue_type") or ""
        rows.append([
            str(bug.get("severity", "medium")),
            str(bug.get("title") or bug.get("description") or bug.get("issue_type") or "Untitled"),
            str(bug.get("workflow_stage") or bug.get("workflow") or "unknown"),
            _shorten(str(evidence), 95),
        ])
    table = Table(rows, colWidths=[0.8 * inch, 2.4 * inch, 1.2 * inch, 2.2 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [table]


def _image_gallery(screenshots: List[Dict[str, Any]], styles) -> List[Any]:
    story: List[Any] = []
    for item in screenshots[:6]:
        label = str(item.get("workflow_stage") or item.get("stage") or item.get("label") or "Screenshot")
        path = str(item.get("artifact_url") or item.get("screenshot_path") or item.get("path") or "").strip()
        resolved = _resolve_path(path)
        if not resolved or not resolved.exists():
            continue
        try:
            image = RLImage(str(resolved), width=5.9 * inch, height=3.4 * inch)
            image.hAlign = "CENTER"
            story.append(Paragraph(_escape(label), styles["BodyTextSmall"]))
            story.append(image)
            story.append(Spacer(1, 0.08 * inch))
        except Exception:
            continue
    if not story:
        story.append(Paragraph("Screenshot assets were not available on disk for embedding.", styles["BodyTextSmall"]))
    return story


def _comparison_paragraphs(comparison: Dict[str, Any], styles) -> List[Any]:
    lines = [
        f"Verdict: {comparison.get('verdict', 'unknown')}",
        comparison.get("summary", ""),
        f"Bug delta: {comparison.get('bug_delta', {})}",
        f"Metric delta: {comparison.get('metrics_delta', {})}",
    ]
    output: List[Any] = []
    for line in lines:
        if line:
            output.append(Paragraph(_escape(str(line)), styles["BodyTextSmall"]))
    return output


def _extract_bugs(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    bugs: List[Dict[str, Any]] = []
    ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
    sections = report.get("report_sections", {}) if isinstance(report.get("report_sections"), dict) else {}
    for source in (
        ai_report.get("detected_bugs"),
        ai_report.get("visual_findings"),
        sections.get("detected_bugs"),
        sections.get("visual_bug_summary"),
    ):
        if isinstance(source, list):
            for bug in source:
                if isinstance(bug, dict):
                    bugs.append(dict(bug))
    return bugs


def _extract_screenshots(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    screenshots = report.get("screenshots", [])
    if not isinstance(screenshots, list):
        return []
    return [item for item in screenshots if isinstance(item, dict)]


def _extract_narrative(report: Dict[str, Any]) -> str:
    ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
    core = ai_report.get("report_core", {}) if isinstance(ai_report.get("report_core"), dict) else {}
    return str(core.get("narrative") or ai_report.get("interaction_narrative") or "").strip()


def _report_run_id(report: Dict[str, Any], fallback: str) -> str:
    debug_data = report.get("debug_data", {}) if isinstance(report.get("debug_data"), dict) else {}
    if debug_data.get("run_id"):
        return str(debug_data.get("run_id"))
    ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
    if ai_report.get("report_core", {}).get("run_id"):
        return str(ai_report.get("report_core", {}).get("run_id"))
    return str(fallback)


def _load_report(report_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    query: Dict[str, Any] = {"report_id": report_id}
    if user_id:
        query["user_id"] = user_id
    report = REPORT_COLLECTION.find_one(query, {"_id": 0})
    if report:
        return report
    query = {"debug_data.run_id": report_id}
    if user_id:
        query["user_id"] = user_id
    report = REPORT_COLLECTION.find_one(query, {"_id": 0})
    if report:
        return report
    raise ValueError(f"Report not found: {report_id}")


def _slugify(value: str) -> str:
    cleaned = [char.lower() if char.isalnum() else "-" for char in value]
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "report"


def _shorten(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[: max(0, length - 3)].rstrip() + "..."


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _page_decorator(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, A4[1] - 0.45 * inch, A4[0] - doc.rightMargin, A4[1] - 0.45 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(doc.leftMargin, 0.35 * inch, "AI Testing Platform")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.35 * inch, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()
