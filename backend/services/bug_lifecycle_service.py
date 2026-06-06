"""Bug lifecycle service — purely event-driven.

This module used to do its own failure detection (``_bugs_from_results``)
and its own status classification (``_derive_status``). That created
two parallel "is this a bug?" decision paths alongside
``create_bugs_from_test`` in :mod:`backend.services.bug_services` and the
``calculate_overall_status`` function in
:mod:`backend.services.scoring.overall_status`. All three occasionally
disagreed about whether a bug existed, what severity it had, and
whether a passing run should close it.

After the centralisation refactor this module is a pure event consumer:

    * The :mod:`backend.services.execution_truth_engine` is the ONLY
      place that decides "is there a bug?" and produces ``BUG_DETECTED``
      / ``BUG_RESOLVED`` events.
    * This module receives those events and projects them into
      ``bug_lifecycle`` MongoDB documents. It never re-interprets raw
      step results.

The legacy public surface (``ingest_bug_lifecycle``,
``reconcile_bugs_on_passing_run``, ``sync_bugs_collection_to_lifecycle``,
``list_bug_lifecycle``, ``summarize_bug_lifecycle``,
``fingerprint_bug``) is preserved for backwards compatibility with
existing callers. The legacy inference helpers have been removed.
"""

from __future__ import annotations

import logging
from collections import Counter
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from pymongo.collection import Collection

from backend.core.models.intelligence_models import BugLifecycleEvent
from backend.database.mongo import db
from backend.services.execution_truth_engine import (
    BUG_EVENT_DETECTED,
    BUG_EVENT_RESOLVED,
    compute_bug_fingerprint,
    diff_resolutions as _diff_resolutions,
)
from backend.services.root_cause_classifier import classify_root_cause
from backend.utils.path_utils import resolve_path

logger = logging.getLogger("services.bug_lifecycle")

BUG_LIFECYCLE_COLLECTION = db["bug_lifecycle"]


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def _ensure_bug_lifecycle_indexes() -> None:
    try:
        BUG_LIFECYCLE_COLLECTION.create_index("fingerprint", unique=True, sparse=True)
        BUG_LIFECYCLE_COLLECTION.create_index([("user_id", 1), ("status", 1)])
        BUG_LIFECYCLE_COLLECTION.create_index([("user_id", 1), ("updated_at", -1)])
    except Exception:
        pass


_ensure_bug_lifecycle_indexes()


# ---------------------------------------------------------------------------
# Public fingerprint helper (kept for compatibility)
# ---------------------------------------------------------------------------

def fingerprint_bug(bug: Dict[str, Any]) -> str:
    """Stable fingerprint for a bug record. Used as the document key.

    Delegates to :func:`backend.services.execution_truth_engine.compute_bug_fingerprint`
    so every caller -- whether the bug was detected by the truth
    engine, manually reported, or imported -- produces the same
    fingerprint string. There is no other fingerprint format in the
    system.
    """
    scenario_id = str(bug.get("scenario_id") or bug.get("objective_id") or "")
    objective_id = str(bug.get("objective_id") or "")
    step_index = bug.get("step_index")
    step_name = str(
        bug.get("step_name")
        or bug.get("failed_step_name")
        or bug.get("title")
        or bug.get("issue_type")
        or bug.get("bug_type")
        or ""
    )
    fingerprint = compute_bug_fingerprint(
        scenario_id=scenario_id,
        objective_id=objective_id,
        step_index=step_index,
        step_name=step_name,
    )
    if fingerprint == "unknown|0|unnamed":
        bug_id = str(bug.get("bug_id") or bug.get("id") or "")
        if bug_id:
            return f"manual|{_normalize_text(bug_id)}"
    return fingerprint


# ---------------------------------------------------------------------------
# Event-driven ingestion
# ---------------------------------------------------------------------------

def ingest_bug_lifecycle(
    run_data: Dict[str, Any],
    report_data: Optional[Dict[str, Any]] = None,
    truth: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Apply truth-engine BUG_DETECTED events to lifecycle documents.

    The historical version of this function walked ``run_data["results"]``
    and ``report_data`` directly looking for failed steps. That is no
    longer the contract. Pass ``truth`` (the canonical object produced
    by :func:`backend.services.execution_truth_engine.evaluate_test_run`)
    and this function will only consume the ``bug_events`` inside it.

    If ``truth`` is omitted, the function will fall back to computing
    one (so legacy callers continue to work) — but the fallback also
    routes through the truth engine, so there is still exactly one
    decision path.
    """
    if truth is None:
        from backend.services.execution_truth_engine import evaluate_test_run
        truth = evaluate_test_run(run_data or {})

    records: List[Dict[str, Any]] = []
    for event in truth.get("bug_events") or []:
        record = _upsert_bug_record_from_truth_event(event, run_data or {})
        records.append(record)
    return records


def reconcile_bugs_on_passing_run(
    run_data: Dict[str, Any],
    report_data: Optional[Dict[str, Any]] = None,
    truth: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Close lifecycle records whose fingerprint is no longer failing.

    The historical version of this function tried to infer from raw
    results which bugs were now passing. The refactored version asks
    the truth engine for the set of ``passing_scenario_fingerprints``,
    looks up the previously-open lifecycle records, and emits
    ``BUG_RESOLVED`` events for every previously-failing fingerprint
    that is NOT in the failing set of the current run.

    If ``truth`` is omitted, the function falls back to computing one
    via the truth engine (no decision logic is duplicated here).
    """
    if truth is None:
        from backend.services.execution_truth_engine import evaluate_test_run
        truth = evaluate_test_run(run_data or {})

    user_id = str(run_data.get("user_id") or (report_data or {}).get("user_id") or "")
    test_id = str(run_data.get("test_id") or (report_data or {}).get("test_run_id") or "")

    open_query: Dict[str, Any] = {
        "status": {"$in": ["Active", "Monitoring", "Regressed", "Flaky", "open", "in-progress"]},
    }
    if user_id:
        open_query["user_id"] = user_id
    if test_id:
        open_query["test_id"] = test_id

    previously_open_fingerprints = [
        str(record.get("fingerprint") or "")
        for record in BUG_LIFECYCLE_COLLECTION.find(open_query, {"fingerprint": 1, "_id": 0})
        if record.get("fingerprint")
    ]

    resolution_events = _diff_resolutions(truth, previously_open_fingerprints)
    return _apply_resolution_events(resolution_events, test_id=test_id, user_id=user_id)


def sync_bugs_collection_to_lifecycle() -> int:
    """One-way mirror: any ``bugs`` document whose status is "resolved"
    or "closed" propagates into the corresponding ``bug_lifecycle`` record.

    Returns the number of lifecycle records that were updated.
    """
    from backend.database.mongo import bug_collection as _bugs  # local import to avoid cycle

    closed_bugs = list(_bugs.find({"status": {"$in": ["resolved", "closed"]}}))
    if not closed_bugs:
        return 0

    updated_count = 0
    now = datetime.utcnow()
    for bug in closed_bugs:
        fingerprint = str(bug.get("fingerprint") or "")
        if not fingerprint:
            continue
        result = BUG_LIFECYCLE_COLLECTION.update_one(
            {"fingerprint": fingerprint},
            {
                "$set": {
                    "status": "Resolved",
                    "last_seen_run_id": bug.get("test_id") or bug.get("execution_id") or "",
                    "updated_at": now,
                    "evidence.mirror_from_bugs": True,
                    "evidence.mirrored_bug_status": bug.get("status"),
                }
            },
        )
        if result.modified_count > 0:
            updated_count += 1
    return updated_count


# ---------------------------------------------------------------------------
# Public read-side helpers (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Internal: truth-event projection
# ---------------------------------------------------------------------------

def _upsert_bug_record_from_truth_event(
    event: Dict[str, Any],
    run_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Project a single ``BUG_DETECTED`` event into a lifecycle document.

    This function is intentionally narrow: it only consumes the
    pre-normalised shape that :func:`evaluate_test_run` produces. It
    does NOT walk raw step results, does NOT apply heuristic
    classification, and does NOT re-derive the failure status.
    """
    if event.get("type") != BUG_EVENT_DETECTED:
        # Resolution events go through _apply_resolution_events instead.
        raise ValueError(f"Unsupported event type for upsert: {event.get('type')}")

    fingerprint = str(event.get("fingerprint") or "")
    if not fingerprint:
        raise ValueError("BUG_DETECTED event missing fingerprint")

    user_id = str(run_data.get("user_id") or "")
    run_id = str(run_data.get("test_id") or run_data.get("run_id") or "")
    severity = str(event.get("severity") or "medium").lower()
    scenario_id = str(event.get("scenario_id") or "")
    step_index = event.get("step_index")
    step_name = str(event.get("step_name") or "")
    error_text = str(event.get("error") or "")

    existing = BUG_LIFECYCLE_COLLECTION.find_one({"fingerprint": fingerprint})
    now = datetime.utcnow()

    evidence = {
        "user_id": user_id,
        "run_id": run_id,
        "scenario_id": scenario_id,
        "step_index": step_index,
        "step_name": step_name,
        "error": error_text,
        "failure_category": event.get("failure_category"),
        "root_cause": event.get("root_cause"),
    }
    history_entry = {
        "run_id": run_id,
        "status": "Active" if not existing else "Active",
        "severity": severity,
        "step_index": step_index,
        "step_name": step_name,
        "error": error_text,
        "root_cause": event.get("root_cause"),
        "created_at": now,
    }

    if existing:
        record = {k: v for k, v in existing.items() if k != "_id"}
        record.setdefault("affected_urls", [])
        record.setdefault("affected_components", [])
        record.setdefault("screenshot_hashes", [])
        record.setdefault("history", [])
        record.setdefault("evidence", {})
        record.setdefault("root_cause_counts", {})
        record["title"] = step_name or record.get("title") or "Detected issue"
        record["description"] = error_text or record.get("description") or ""
        record["severity"] = _max_severity(record.get("severity", "medium"), severity)
        # When a previously-Resolved bug re-appears, it is a regression.
        if str(record.get("status", "")) == "Resolved":
            record["status"] = "Regressed"
            record["regression_count"] = int(record.get("regression_count", 0) or 0) + 1
        else:
            record["status"] = "Active" if severity in {"high", "critical"} else record.get("status") or "Monitoring"
        record["scenario_id"] = scenario_id or record.get("scenario_id")
        record["objective_id"] = event.get("objective_id") or record.get("objective_id")
        record["last_seen_run_id"] = run_id
        record["occurrences"] = int(record.get("occurrences", 0)) + 1
        if run_data.get("url") and run_data["url"] not in record["affected_urls"]:
            record["affected_urls"].append(run_data["url"])
        record["evidence"].update({k: v for k, v in evidence.items() if v is not None})
        record["history"].append(history_entry)
        record["updated_at"] = now
        BUG_LIFECYCLE_COLLECTION.replace_one({"_id": existing["_id"]}, record)
        return record

    record = {
        "bug_id": fingerprint[:16],
        "fingerprint": fingerprint,
        "user_id": user_id,
        "test_id": run_id,
        "title": step_name or "Detected issue",
        "description": error_text or "",
        "severity": severity,
        "status": "Active" if severity in {"high", "critical"} else "Monitoring",
        "scenario_id": scenario_id or None,
        "objective_id": event.get("objective_id") or None,
        "feature_key": None,
        "first_seen_run_id": run_id,
        "last_seen_run_id": run_id,
        "regression_count": 0,
        "resolved_count": 0,
        "flaky_count": 0,
        "root_cause": event.get("root_cause") or "UNKNOWN",
        "root_cause_confidence": 0.0,
        "root_cause_counts": {str(event.get("root_cause") or "UNKNOWN"): 1},
        "most_common_root_cause": str(event.get("root_cause") or "UNKNOWN"),
        "affected_components": [],
        "affected_urls": [run_data["url"]] if run_data.get("url") else [],
        "screenshot_hashes": [],
        "history": [history_entry],
        "evidence": evidence,
        "created_at": now,
        "updated_at": now,
    }
    BUG_LIFECYCLE_COLLECTION.insert_one(record)
    record.pop("_id", None)
    return record


def _apply_resolution_events(
    events: List[Dict[str, Any]],
    *,
    test_id: str,
    user_id: str,
) -> List[Dict[str, Any]]:
    """Apply BUG_RESOLVED events to lifecycle documents."""
    resolved: List[Dict[str, Any]] = []
    now = datetime.utcnow()
    for event in events:
        if event.get("type") != BUG_EVENT_RESOLVED:
            continue
        fingerprint = str(event.get("fingerprint") or "")
        if not fingerprint:
            continue
        history_entry = {
            "run_id": test_id,
            "status": "Resolved",
            "resolution_reason": event.get("resolution_reason") or "regression_pass",
            "created_at": now,
        }
        BUG_LIFECYCLE_COLLECTION.update_one(
            {"fingerprint": fingerprint},
            {
                "$set": {
                    "status": "Resolved",
                    "last_seen_run_id": test_id,
                    "resolved_count": 1,  # incremented below if existing
                    "evidence.resolved": True,
                    "evidence.resolution_reason": event.get("resolution_reason") or "regression_pass",
                    "evidence.resolved_in_run_id": test_id,
                    "updated_at": now,
                },
                "$push": {"history": history_entry},
            },
        )
        # Read the existing record so we can increment resolved_count
        # properly (update_one's $inc would also work but this is more
        # explicit and works in sharded/test environments).
        existing = BUG_LIFECYCLE_COLLECTION.find_one({"fingerprint": fingerprint}, {"_id": 0})
        if existing:
            BUG_LIFECYCLE_COLLECTION.update_one(
                {"fingerprint": fingerprint},
                {"$set": {"resolved_count": int(existing.get("resolved_count", 0) or 0) + 1}},
            )
            updated = BUG_LIFECYCLE_COLLECTION.find_one({"fingerprint": fingerprint}, {"_id": 0})
            if updated:
                resolved.append(updated)

        # Mirror the resolution into the canonical ``bug_collection`` so
        # the dashboard "open bug" count is derived from the same source
        # of truth as the bug status. We only touch status / resolved_at
        # / evidence fields -- we never overwrite the user-set history,
        # severity, or any other field on the ``bug_collection`` document.
        _mirror_resolution_to_bug_collection(
            fingerprint=fingerprint,
            test_id=test_id,
            resolution_reason=event.get("resolution_reason") or "regression_pass",
        )
    return resolved


def _mirror_resolution_to_bug_collection(
    *,
    fingerprint: str,
    test_id: str,
    resolution_reason: str,
) -> int:
    """One-way mirror: close matching ``bug_collection`` documents when
    the lifecycle says a bug is resolved.

    The dashboard "open" count queries ``bug_collection`` by status; if
    a bug is resolved in the lifecycle but stays "open" in
    ``bug_collection`` the count will be wrong. This helper closes
    every ``bug_collection`` document whose ``fingerprint`` matches the
    resolved one. It never deletes documents, never touches
    ``history`` or any other user-set field, and it is a no-op when
    there is no matching record.
    """
    if not fingerprint:
        return 0
    try:
        from backend.database.mongo import bug_collection as _bugs  # local import to avoid cycle
    except Exception:
        return 0
    now = datetime.utcnow()
    try:
        result = _bugs.update_many(
            {"fingerprint": fingerprint, "status": {"$nin": ["resolved", "closed", "Resolved", "Closed"]}},
            {
                "$set": {
                    "status": "resolved",
                    "resolved_at": now,
                    "updated_at": now,
                    "resolution_reason": resolution_reason,
                    "resolved_in_run_id": test_id,
                },
            },
        )
        return int(result.modified_count or 0)
    except Exception:
        logger.exception("Failed to mirror resolution to bug_collection for fingerprint=%s", fingerprint)
        return 0


# ---------------------------------------------------------------------------
# Backwards-compat shims (legacy public surface retained)
# ---------------------------------------------------------------------------
#
# ``_stable_fingerprint`` was a SHA-256-based generator that produced
# fingerprints in a different format from the truth engine. It has been
# removed. New code MUST call
# :func:`backend.services.execution_truth_engine.compute_bug_fingerprint`
# (or the ``fingerprint_bug`` shim above) so the system has exactly one
# fingerprint format.

def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _max_severity(left: str, right: str) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    left_key = str(left or "low").lower()
    right_key = str(right or "low").lower()
    return left_key if order.get(left_key, 0) >= order.get(right_key, 0) else right_key


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _normalize_lifecycle_status(value: Any) -> str:
    status = str(value or "monitoring").strip().lower()
    if status in {"active", "resolved", "regressed", "flaky", "monitoring"}:
        return status
    return "monitoring"


def _format_lifecycle_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


# Silence the unused import warnings from the legacy shims that
# re-exports the same helpers as before.
_ = (
    BugLifecycleEvent,
    Collection,
    classify_root_cause,
    deepcopy,
    _normalize_lifecycle_status,
    _format_lifecycle_datetime,
)


# ---------------------------------------------------------------------------
# Image fingerprint helpers (used by run_comparison_service)
# ---------------------------------------------------------------------------

def _image_hash(path: Optional[str]) -> Optional[str]:
    """Compute a perceptual hash for a screenshot file.

    Returns a 16-character hex string, or ``None`` when the path is
    missing, non-filesystem, or unreadable. This is a perceptual
    difference hash (dHash) over an 8x8 greyscale thumbnail of the
    image; it is intentionally cheap and only suitable for
    near-duplicate detection.
    """
    if not path:
        return None
    resolved = resolve_path(path)
    if not resolved or not resolved.exists():
        return None
    try:
        from PIL import Image

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


def _hash_similarity(left: Optional[str], right: Optional[str]) -> float:
    """Return 0.0-1.0 similarity between two perceptual hex hashes.

    Uses Hamming distance over the binary representation of the
    hashes. A value of 1.0 means the hashes are identical, 0.0 means
    they differ in every bit.
    """
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
