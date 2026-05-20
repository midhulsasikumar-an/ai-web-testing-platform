from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core.models.intelligence_models import ComparisonScreenshotResult, RunComparisonResult
from backend.database.mongo import db, run_comparison_collection
from backend.services.bug_lifecycle_service import fingerprint_bug, _image_hash, _hash_similarity, _resolve_path

REPORT_COLLECTION = db["reports"]


def compare_runs(
    baseline_run_id: str,
    comparison_run_id: str,
    *,
    user_id: Optional[str] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    baseline_report = _load_report(baseline_run_id, user_id=user_id)
    comparison_report = _load_report(comparison_run_id, user_id=user_id)
    comparison_id = str(uuid.uuid4())

    baseline_metrics = _extract_metrics(baseline_report)
    comparison_metrics = _extract_metrics(comparison_report)
    metrics_delta = _compute_metric_delta(baseline_metrics, comparison_metrics)

    baseline_bugs = _extract_bugs(baseline_report)
    comparison_bugs = _extract_bugs(comparison_report)
    bug_delta = _compare_bugs(baseline_bugs, comparison_bugs)

    screenshot_deltas = _compare_screenshots(baseline_report, comparison_report)

    verdict = _derive_verdict(metrics_delta, bug_delta)
    summary = _build_summary(verdict, metrics_delta, bug_delta, screenshot_deltas)

    result = RunComparisonResult(
        comparison_id=comparison_id,
        baseline_run_id=baseline_run_id,
        comparison_run_id=comparison_run_id,
        baseline_report_id=baseline_report.get("report_id"),
        comparison_report_id=comparison_report.get("report_id"),
        verdict=verdict,
        summary=summary,
        metrics_delta=metrics_delta,
        bug_delta=bug_delta,
        screenshot_deltas=screenshot_deltas,
        baseline={
            "report_id": baseline_report.get("report_id"),
            "run_id": _run_id_from_report(baseline_report, baseline_run_id),
            "status": baseline_report.get("status"),
            "execution_summary": baseline_report.get("execution_summary", {}),
            "coverage": baseline_report.get("coverage", {}),
            "ai_report": baseline_report.get("ai_report", {}),
        },
        comparison={
            "report_id": comparison_report.get("report_id"),
            "run_id": _run_id_from_report(comparison_report, comparison_run_id),
            "status": comparison_report.get("status"),
            "execution_summary": comparison_report.get("execution_summary", {}),
            "coverage": comparison_report.get("coverage", {}),
            "ai_report": comparison_report.get("ai_report", {}),
        },
    ).model_dump(mode="json")

    if persist:
        payload = dict(result)
        payload["user_id"] = user_id or baseline_report.get("user_id") or comparison_report.get("user_id") or ""
        payload["created_at"] = datetime.utcnow()
        run_comparison_collection.insert_one(payload)

    return result


def list_run_comparisons(run_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if run_id:
        query["$or"] = [{"baseline_run_id": run_id}, {"comparison_run_id": run_id}]
    return list(run_comparison_collection.find(query, {"_id": 0}).sort("created_at", -1))


def _load_report(identifier: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    query: Dict[str, Any] = {"report_id": identifier}
    if user_id:
        query["user_id"] = user_id
    report = REPORT_COLLECTION.find_one(query, {"_id": 0})
    if report:
        return report
    query = {"debug_data.run_id": identifier}
    if user_id:
        query["user_id"] = user_id
    report = REPORT_COLLECTION.find_one(query, {"_id": 0})
    if report:
        return report
    raise ValueError(f"Report not found for identifier: {identifier}")


def _extract_metrics(report: Dict[str, Any]) -> Dict[str, float]:
    summary = report.get("execution_summary", {}) if isinstance(report.get("execution_summary"), dict) else {}
    coverage = report.get("coverage", {}) if isinstance(report.get("coverage"), dict) else {}
    ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
    success_scoring = ai_report.get("success_scoring", {}) if isinstance(ai_report.get("success_scoring"), dict) else {}

    return {
        "website_health_score": float(report.get("website_health_score", 0) or 0),
        "workflow_completion": float(report.get("workflow_completion", 0.0) or 0.0),
        "success_rate": float(summary.get("success_rate", 0.0) or 0.0),
        "pages_visited": float(summary.get("pages_visited", 0) or 0),
        "actions_executed": float(summary.get("actions_executed", 0) or 0),
        "recoveries_triggered": float(summary.get("recoveries_triggered", 0) or 0),
        "duration_seconds": float(summary.get("duration_seconds", 0.0) or 0.0),
        "coverage_score": float(coverage.get("coverage_score", 0) or 0),
        "critical_issues": float(report.get("critical_issues", 0) or 0),
        "high_issues": float(report.get("high_issues", 0) or 0),
        "medium_issues": float(report.get("medium_issues", 0) or 0),
        "low_issues": float(report.get("low_issues", 0) or 0),
        "success_score": float(success_scoring.get("overall_score", 0.0) or 0.0),
    }


def _compute_metric_delta(baseline: Dict[str, float], comparison: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    deltas: Dict[str, Dict[str, float]] = {}
    for key, baseline_value in baseline.items():
        comparison_value = comparison.get(key, 0.0)
        deltas[key] = {
            "baseline": baseline_value,
            "comparison": comparison_value,
            "delta": comparison_value - baseline_value,
        }
    return deltas


def _extract_bugs(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    bugs: List[Dict[str, Any]] = []
    ai_report = report.get("ai_report", {}) if isinstance(report.get("ai_report"), dict) else {}
    sections = report.get("report_sections", {}) if isinstance(report.get("report_sections"), dict) else {}
    for source in (
        ai_report.get("detected_bugs"),
        ai_report.get("visual_findings"),
        sections.get("detected_bugs"),
        sections.get("visual_bug_summary"),
        report.get("debug_data", {}).get("detected_bugs") if isinstance(report.get("debug_data"), dict) else None,
        report.get("debug_data", {}).get("visual_bug_summary") if isinstance(report.get("debug_data"), dict) else None,
    ):
        if isinstance(source, list):
            for bug in source:
                if isinstance(bug, dict):
                    bug = dict(bug)
                    bug["fingerprint"] = fingerprint_bug_from_record(bug)
                    bugs.append(bug)
    return bugs


def _compare_bugs(baseline_bugs: List[Dict[str, Any]], comparison_bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    baseline_map = {bug["fingerprint"]: bug for bug in baseline_bugs if bug.get("fingerprint")}
    comparison_map = {bug["fingerprint"]: bug for bug in comparison_bugs if bug.get("fingerprint")}

    shared = sorted(set(baseline_map).intersection(comparison_map))
    baseline_only = sorted(set(baseline_map).difference(comparison_map))
    comparison_only = sorted(set(comparison_map).difference(baseline_map))

    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    changed_severity: List[Dict[str, Any]] = []
    for fingerprint in shared:
        left = str(baseline_map[fingerprint].get("severity", "medium")).lower()
        right = str(comparison_map[fingerprint].get("severity", "medium")).lower()
        if left != right:
            changed_severity.append({
                "fingerprint": fingerprint,
                "baseline_severity": left,
                "comparison_severity": right,
                "delta": severity_order.get(right, 0) - severity_order.get(left, 0),
            })

    return {
        "baseline_bug_count": len(baseline_bugs),
        "comparison_bug_count": len(comparison_bugs),
        "shared_bugs": len(shared),
        "new_bugs": len(comparison_only),
        "resolved_bugs": len(baseline_only),
        "new_bug_fingerprints": comparison_only,
        "resolved_bug_fingerprints": baseline_only,
        "changed_severity": changed_severity,
    }


def _compare_screenshots(baseline_report: Dict[str, Any], comparison_report: Dict[str, Any]) -> List[ComparisonScreenshotResult]:
    baseline_screens = _index_screenshots(baseline_report)
    comparison_screens = _index_screenshots(comparison_report)
    matched_stages = sorted(set(baseline_screens).intersection(comparison_screens))
    results: List[ComparisonScreenshotResult] = []
    for stage in matched_stages[:8]:
        left = baseline_screens.get(stage)
        right = comparison_screens.get(stage)
        left_hash = _image_hash(left) if left else None
        right_hash = _image_hash(right) if right else None
        similarity = 1.0
        difference = 0.0
        if left_hash and right_hash:
            similarity = _hash_similarity(left_hash, right_hash)
            difference = 1.0 - similarity
        results.append(
            ComparisonScreenshotResult(
                baseline=left,
                candidate=right,
                similarity=similarity,
                difference=difference,
                baseline_hash=left_hash,
                candidate_hash=right_hash,
            )
        )
    return results


def _index_screenshots(report: Dict[str, Any]) -> Dict[str, str]:
    screenshots: Dict[str, str] = {}
    for source in (
        report.get("screenshots"),
        report.get("ai_report", {}).get("screenshots") if isinstance(report.get("ai_report"), dict) else None,
        report.get("report_sections", {}).get("screenshots") if isinstance(report.get("report_sections"), dict) else None,
    ):
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            stage = str(item.get("workflow_stage") or item.get("stage") or item.get("label") or "unknown")
            path = str(item.get("artifact_url") or item.get("screenshot_path") or item.get("path") or "").strip()
            if stage not in screenshots and path:
                screenshots[stage] = path
    return screenshots


def _derive_verdict(metrics_delta: Dict[str, Dict[str, float]], bug_delta: Dict[str, Any]) -> str:
    health_delta = metrics_delta.get("website_health_score", {}).get("delta", 0.0)
    workflow_delta = metrics_delta.get("workflow_completion", {}).get("delta", 0.0)
    success_delta = metrics_delta.get("success_score", {}).get("delta", 0.0)
    new_bugs = int(bug_delta.get("new_bugs", 0) or 0)
    resolved_bugs = int(bug_delta.get("resolved_bugs", 0) or 0)

    if health_delta > 5 and workflow_delta >= 0 and new_bugs == 0:
        return "improved"
    if new_bugs > resolved_bugs and (health_delta < -3 or success_delta < 0):
        return "regressed"
    if abs(health_delta) <= 2 and abs(workflow_delta) <= 0.05 and new_bugs == resolved_bugs:
        return "stable"
    if resolved_bugs > new_bugs:
        return "recovered"
    return "changed"


def _build_summary(
    verdict: str,
    metrics_delta: Dict[str, Dict[str, float]],
    bug_delta: Dict[str, Any],
    screenshot_deltas: List[ComparisonScreenshotResult],
) -> str:
    health_delta = metrics_delta.get("website_health_score", {}).get("delta", 0.0)
    workflow_delta = metrics_delta.get("workflow_completion", {}).get("delta", 0.0)
    return (
        f"Comparison verdict: {verdict}. "
        f"Health score changed by {health_delta:+.1f}, workflow completion changed by {workflow_delta:+.2f}, "
        f"{int(bug_delta.get('new_bugs', 0) or 0)} new bug(s), {int(bug_delta.get('resolved_bugs', 0) or 0)} resolved bug(s), "
        f"and {len(screenshot_deltas)} matched screenshot pair(s) analyzed."
    )


def _run_id_from_report(report: Dict[str, Any], fallback: str) -> str:
    if isinstance(report.get("debug_data"), dict) and report["debug_data"].get("run_id"):
        return str(report["debug_data"]["run_id"])
    return str(fallback)


def fingerprint_bug_from_record(bug: Dict[str, Any]) -> str:
    title = str(bug.get("title") or bug.get("description") or bug.get("technical_explanation") or bug.get("issue_type") or bug.get("bug_type") or "")
    description = str(bug.get("description") or bug.get("details") or bug.get("technical_explanation") or "")
    severity = str(bug.get("severity") or bug.get("risk_level") or "medium")
    workflow_stage = str(bug.get("workflow_stage") or bug.get("workflow") or bug.get("page_type") or "unknown")
    url = str(bug.get("url") or bug.get("artifact_url") or "")
    selector = str(bug.get("selector") or bug.get("locator") or bug.get("target") or "")
    issue_type = str(bug.get("issue_type") or bug.get("bug_type") or bug.get("category") or "unknown")
    component = str(bug.get("affected_component") or bug.get("component") or workflow_stage or "unknown")
    evidence = bug.get("evidence") if isinstance(bug.get("evidence"), dict) else {}
    return fingerprint_bug(
        title=title,
        description=description,
        severity=severity,
        workflow_stage=workflow_stage,
        url=url,
        selector=selector,
        issue_type=issue_type,
        component=component,
        evidence=evidence,
    )
