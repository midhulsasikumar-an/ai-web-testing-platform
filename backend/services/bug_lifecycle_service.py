from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from PIL import Image
from pymongo.collection import Collection

from backend.core.models.intelligence_models import BugLifecycleEvent
from backend.database.mongo import db

BUG_LIFECYCLE_COLLECTION = db["bug_lifecycle"]


def fingerprint_bug(bug: Dict[str, Any]) -> str:
    return _fingerprint_bug(
        title=str(bug.get("title") or bug.get("description") or bug.get("technical_explanation") or bug.get("issue_type") or bug.get("bug_type") or ""),
        description=str(bug.get("description") or bug.get("details") or bug.get("technical_explanation") or ""),
        severity=str(bug.get("severity") or bug.get("risk_level") or "medium"),
        workflow_stage=str(bug.get("workflow_stage") or bug.get("workflow") or bug.get("page_type") or "unknown"),
        url=str(bug.get("url") or bug.get("artifact_url") or ""),
        selector=str(bug.get("selector") or bug.get("locator") or bug.get("target") or ""),
        issue_type=str(bug.get("issue_type") or bug.get("bug_type") or bug.get("category") or "unknown"),
        component=str(bug.get("affected_component") or bug.get("component") or bug.get("workflow_stage") or bug.get("workflow") or "unknown"),
        evidence=bug.get("evidence") if isinstance(bug.get("evidence"), dict) else {},
    )


def ingest_bug_lifecycle(
    run_data: Dict[str, Any],
    report_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    bugs = _extract_bug_events(run_data, report_data)
    records: List[Dict[str, Any]] = []
    for bug in bugs:
        record = _upsert_bug_record(bug)
        records.append(record)
    return records


def list_bug_lifecycle(
    *,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    website: Optional[str] = None,
    workflow_stage: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status
    if website:
        query["website"] = website
    if workflow_stage:
        query["workflow_stage"] = workflow_stage
    return list(BUG_LIFECYCLE_COLLECTION.find(query, {"_id": 0}).sort("updated_at", -1))


def summarize_bug_lifecycle(user_id: Optional[str] = None) -> Dict[str, Any]:
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    records = list(BUG_LIFECYCLE_COLLECTION.find(query, {"_id": 0}))
    by_status = Counter(str(record.get("status", "Monitoring")) for record in records)
    by_website = Counter(str(record.get("website", "unknown")) for record in records)
    by_workflow = Counter(str(record.get("workflow_stage", "unknown")) for record in records)
    recurring = [record for record in records if int(record.get("occurrences", 0)) > 1]
    regressions = [record for record in records if int(record.get("regression_count", 0)) > 0]
    return {
        "total_bugs": len(records),
        "by_status": dict(by_status),
        "by_website": dict(by_website),
        "by_workflow_stage": dict(by_workflow),
        "recurring_bugs": len(recurring),
        "regressed_bugs": len(regressions),
        "records": records,
    }


def _extract_bug_events(run_data: Dict[str, Any], report_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    run_id = str(run_data.get("run_id") or report_data.get("debug_data", {}).get("run_id") if report_data else "")
    report_id = str(report_data.get("report_id") if report_data else "")
    user_id = str((report_data or {}).get("user_id") or run_data.get("user_id") or "")
    goal = str(run_data.get("goal") or report_data.get("goal") or "")
    start_url = str(run_data.get("start_url") or run_data.get("url") or report_data.get("start_url") or "")
    screenshots = _collect_screenshot_map(run_data, report_data)

    raw_bugs: List[Dict[str, Any]] = []
    if report_data:
        raw_bugs.extend(_as_list(report_data.get("ai_report", {}).get("detected_bugs")))
        raw_bugs.extend(_as_list(report_data.get("ai_report", {}).get("visual_findings")))
        raw_bugs.extend(_as_list(report_data.get("report_sections", {}).get("detected_bugs")))
        raw_bugs.extend(_as_list(report_data.get("report_sections", {}).get("visual_bug_summary")))
    raw_bugs.extend(_as_list(run_data.get("detected_bugs")))
    raw_bugs.extend(_as_list(run_data.get("visual_bug_summary")))

    events: List[Dict[str, Any]] = []
    for index, bug in enumerate(raw_bugs):
        if not isinstance(bug, dict):
            continue
            normalized = _normalize_bug(
                bug,
                index=index,
                goal=goal,
                start_url=start_url,
                run_id=run_id,
                report_id=report_id,
                user_id=user_id,
            )
        if not normalized:
            continue
        if not normalized.get("screenshot_path") and normalized.get("workflow_stage") in screenshots:
            normalized["screenshot_path"] = screenshots[normalized["workflow_stage"]]
        events.append(normalized)
    return events


def _normalize_bug(
    bug: Dict[str, Any],
    *,
    index: int,
    goal: str,
    start_url: str,
    run_id: str,
    report_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    title = str(
        bug.get("title")
        or bug.get("description")
        or bug.get("technical_explanation")
        or bug.get("issue_type")
        or bug.get("bug_type")
        or bug.get("name")
        or f"Bug {index + 1}"
    ).strip()
    description = str(bug.get("description") or bug.get("details") or bug.get("technical_explanation") or "").strip()
    severity = str(bug.get("severity") or bug.get("risk_level") or "medium").lower()
    workflow_stage = str(bug.get("workflow_stage") or bug.get("workflow") or bug.get("page_type") or "unknown")
    url = str(bug.get("url") or bug.get("artifact_url") or start_url or "")
    selector = str(bug.get("selector") or bug.get("locator") or bug.get("target") or "")
    issue_type = str(bug.get("issue_type") or bug.get("bug_type") or bug.get("category") or "unknown")
    component = str(bug.get("affected_component") or bug.get("component") or workflow_stage or "unknown")
    screenshot_path = _extract_screenshot_path(bug)
    evidence = deepcopy(bug.get("evidence") or {})
    evidence.setdefault("goal", goal)
    evidence.setdefault("workflow_stage", workflow_stage)
    evidence.setdefault("selector", selector)
    evidence.setdefault("issue_type", issue_type)
    evidence.setdefault("run_id", run_id)
    evidence.setdefault("report_id", report_id)
    fingerprint = _fingerprint_bug(
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
    screenshot_hash = _image_hash(screenshot_path)
    return BugLifecycleEvent(
        bug_id=str(bug.get("bug_id") or fingerprint[:16]),
        fingerprint=fingerprint,
        title=title,
        description=description,
        severity=severity,
        workflow_stage=workflow_stage,
        run_id=run_id,
        report_id=report_id,
        url=url,
        screenshot_path=screenshot_path,
        screenshot_hash=screenshot_hash,
        evidence={**evidence, "user_id": user_id},
    ).model_dump(mode="json")


def _upsert_bug_record(event: Dict[str, Any]) -> Dict[str, Any]:
    fingerprint = str(event["fingerprint"])
    existing = BUG_LIFECYCLE_COLLECTION.find_one({"fingerprint": fingerprint})
    screenshot_hash = event.get("screenshot_hash")
    similarity = _best_screenshot_similarity(existing, screenshot_hash) if screenshot_hash else None
    next_status = _derive_status(existing, event, similarity)
    now = datetime.utcnow()
    history_entry = {
        "run_id": event.get("run_id"),
        "report_id": event.get("report_id"),
        "status": next_status,
        "severity": event.get("severity"),
        "workflow_stage": event.get("workflow_stage"),
        "url": event.get("url"),
        "screenshot_path": event.get("screenshot_path"),
        "screenshot_hash": event.get("screenshot_hash"),
        "similarity_to_previous": similarity,
        "created_at": now,
    }

    if existing:
        record = {k: v for k, v in existing.items() if k != "_id"}
        record.setdefault("affected_components", [])
        record.setdefault("affected_urls", [])
        record.setdefault("screenshot_hashes", [])
        record.setdefault("history", [])
        record.setdefault("evidence", {})
        record["title"] = event.get("title", record.get("title", ""))
        record["description"] = event.get("description", record.get("description", ""))
        record["severity"] = _max_severity(record.get("severity", "medium"), event.get("severity", "medium"))
        record["status"] = next_status
        record["workflow_stage"] = event.get("workflow_stage") or record.get("workflow_stage", "unknown")
        record["website"] = _extract_website(event.get("url") or record.get("website", ""))
        record["last_seen_run_id"] = event.get("run_id") or record.get("last_seen_run_id", "")
        record["occurrences"] = int(record.get("occurrences", 0)) + 1
        if next_status == "Regressed":
            record["regression_count"] = int(record.get("regression_count", 0)) + 1
        if next_status == "Resolved":
            record["resolved_count"] = int(record.get("resolved_count", 0)) + 1
        if next_status == "Flaky":
            record["flaky_count"] = int(record.get("flaky_count", 0)) + 1
        for value in [event.get("workflow_stage"), event.get("evidence", {}).get("goal")]:
            if value:
                candidate = str(value)
                if candidate not in record["affected_components"]:
                    record["affected_components"].append(candidate)
        if event.get("url") and event["url"] not in record["affected_urls"]:
            record["affected_urls"].append(event["url"])
        if screenshot_hash and screenshot_hash not in record["screenshot_hashes"]:
            record["screenshot_hashes"].append(screenshot_hash)
        record["evidence"].update({k: v for k, v in event.get("evidence", {}).items() if v is not None})
        record["history"].append(history_entry)
        record["updated_at"] = now
        BUG_LIFECYCLE_COLLECTION.replace_one({"_id": existing["_id"]}, record)
        return record

    record = {
        "bug_id": event["bug_id"],
        "fingerprint": fingerprint,
    "user_id": str(event.get("evidence", {}).get("user_id") or ""),
        "user_id": str(event.get("evidence", {}).get("user_id") or ""),
        "title": event.get("title", ""),
        "description": event.get("description", ""),
        "severity": event.get("severity", "medium"),
        "status": next_status,
        "website": _extract_website(event.get("url", "")),
        "workflow_stage": event.get("workflow_stage", "unknown"),
        "first_seen_run_id": event.get("run_id", ""),
        "last_seen_run_id": event.get("run_id", ""),
                "user_id": str(event.get("evidence", {}).get("user_id") or ""),
        "regression_count": 0,
        "resolved_count": 0,
        "flaky_count": 0,
        "affected_components": [value for value in [event.get("workflow_stage"), event.get("evidence", {}).get("goal")] if value],
        "affected_urls": [event.get("url")] if event.get("url") else [],
        "screenshot_hashes": [event.get("screenshot_hash")] if event.get("screenshot_hash") else [],
        "history": [history_entry],
        "evidence": deepcopy(event.get("evidence", {})),
        "created_at": now,
        "updated_at": now,
    }
    BUG_LIFECYCLE_COLLECTION.insert_one(record)
    return record


def _derive_status(existing: Optional[Dict[str, Any]], event: Dict[str, Any], similarity: Optional[float]) -> str:
    severity = str(event.get("severity", "medium")).lower()
    if event.get("evidence", {}).get("resolved") or event.get("status") == "resolved":
        return "Resolved"
    if not existing:
        return "Active" if severity in {"high", "critical"} else "Monitoring"
    previous_status = str(existing.get("status", "Monitoring"))
    if previous_status == "Resolved":
        return "Regressed"
    if similarity is not None and similarity < 0.82 and int(existing.get("occurrences", 1)) >= 2:
        return "Flaky"
    if int(existing.get("regression_count", 0)) > 0:
        return "Regressed"
    if int(existing.get("flaky_count", 0)) > 1:
        return "Flaky"
    if severity in {"critical", "high"}:
        return "Active"
    return previous_status if previous_status in {"Active", "Flaky", "Monitoring"} else "Monitoring"


def _fingerprint_bug(
    *,
    title: str,
    description: str,
    severity: str,
    workflow_stage: str,
    url: str,
    selector: str,
    issue_type: str,
    component: str,
    evidence: Dict[str, Any],
) -> str:
    stable_parts = [
        _normalize_text(title),
        _normalize_text(description),
        _normalize_text(severity),
        _normalize_text(workflow_stage),
        _normalize_text(url),
        _normalize_text(selector),
        _normalize_text(issue_type),
        _normalize_text(component),
        _normalize_text(evidence.get("technical_explanation", "")),
        _normalize_text(evidence.get("root_cause", "")),
        _normalize_text(evidence.get("message", "")),
        _normalize_text(evidence.get("validation_type", "")),
    ]
    digest_source = "|".join(stable_parts)
    return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()


def _best_screenshot_similarity(existing: Optional[Dict[str, Any]], screenshot_hash: Optional[str]) -> Optional[float]:
    if not existing or not screenshot_hash:
        return None
    prior_hashes = [str(value) for value in existing.get("screenshot_hashes", []) if value]
    if not prior_hashes:
        return None
    return max((_hash_similarity(screenshot_hash, prior_hash) for prior_hash in prior_hashes), default=None)


def _hash_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    try:
        left_int = int(left, 16)
        right_int = int(right, 16)
    except ValueError:
        return 0.0
    xor_value = left_int ^ right_int
    distance = xor_value.bit_count()
    width = max(left_int.bit_length(), right_int.bit_length(), 64)
    return max(0.0, 1.0 - (distance / width))


def _image_hash(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    resolved = _resolve_path(path)
    if not resolved or not resolved.exists():
        return None
    try:
        with Image.open(resolved) as image:
            image = image.convert("L").resize((9, 8))
            pixels = list(image.getdata())
            bits = []
            for row in range(8):
                offset = row * 9
                for column in range(8):
                    bits.append(1 if pixels[offset + column] > pixels[offset + column + 1] else 0)
            value = 0
            for bit in bits:
                value = (value << 1) | bit
            return f"{value:016x}"
    except Exception:
        return None


def _extract_screenshot_path(bug: Dict[str, Any]) -> Optional[str]:
    for key in ("screenshot_path", "artifact_url", "image", "path"):
        value = bug.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    evidence = bug.get("evidence") or {}
    if isinstance(evidence, dict):
        for key in ("screenshot_path", "artifact_url", "path"):
            value = evidence.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _collect_screenshot_map(run_data: Dict[str, Any], report_data: Optional[Dict[str, Any]]) -> Dict[str, str]:
    screenshot_map: Dict[str, str] = {}
    sources: List[Dict[str, Any]] = []
    sources.extend(_as_list(run_data.get("screenshots")))
    if report_data:
        sources.extend(_as_list(report_data.get("screenshots")))
        sources.extend(_as_list(report_data.get("ai_report", {}).get("screenshots")))
    for item in sources:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("workflow_stage") or item.get("stage") or item.get("label") or "").strip()
        path = _extract_screenshot_path(item)
        if stage and path and stage not in screenshot_map:
            screenshot_map[stage] = path
    return screenshot_map


def _extract_website(url: str) -> str:
    if not url:
        return "unknown"
    parsed = urlparse(url)
    return parsed.netloc or parsed.path or "unknown"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _max_severity(left: str, right: str) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    left_key = str(left or "low").lower()
    right_key = str(right or "low").lower()
    return left_key if order.get(left_key, 0) >= order.get(right_key, 0) else right_key


def _resolve_path(path: str) -> Optional[Path]:
    raw = str(path).strip().replace("\\", "/")
    if raw.startswith("http://") or raw.startswith("https://"):
        return None
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    project_root = Path(__file__).resolve().parents[2]
    return (project_root / raw).resolve()


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]
