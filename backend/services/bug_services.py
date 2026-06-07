import uuid
from datetime import datetime
from backend.database.mongo import bug_collection
from backend.services.failure_classifier import classify_failure_category
from backend.services.root_cause_classifier import classify_root_cause
from backend.services.execution_truth_engine import BUG_EVENT_DETECTED, compute_bug_fingerprint


GENERIC_FALLBACKS = [
    "Button Interaction Failure",
    "Link Navigation Failure",
    "Input Validation Failure",
    "Page Load Failure",
    "Missing Element",
    "Screenshot Mismatch",
    "Accessibility Issue",
    "Performance Issue",
    "Login Failure",
    "Form Submission Failure",
]


def _shorten(value: str, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _normalize_issue_type(issue_type: str) -> str:
    value = (issue_type or "").strip()
    if not value:
        return ""
    return _shorten(" ".join(part.capitalize() for part in value.replace("_", " ").split()), 50)


def _classify_generated_title(*parts: str) -> str:
    haystack = " ".join((part or "").lower() for part in parts)

    if any(keyword in haystack for keyword in ["button", "click"]):
        return "Button Interaction Failure"
    if any(keyword in haystack for keyword in ["link", "navigate", "navigation", "redirect"]):
        return "Link Navigation Failure"
    if any(keyword in haystack for keyword in ["validation", "invalid", "required", "input"]):
        return "Input Validation Failure"
    if any(keyword in haystack for keyword in ["load", "timeout", "network", "page"]):
        return "Page Load Failure"
    if any(keyword in haystack for keyword in ["missing", "not found", "locator"]):
        return "Missing Element"
    if any(keyword in haystack for keyword in ["screenshot", "visual", "pixel"]):
        return "Screenshot Mismatch"
    if any(keyword in haystack for keyword in ["accessibility", "aria", "contrast", "a11y"]):
        return "Accessibility Issue"
    if any(keyword in haystack for keyword in ["performance", "slow", "latency"]):
        return "Performance Issue"
    if any(keyword in haystack for keyword in ["login", "auth", "credential", "password"]):
        return "Login Failure"
    if any(keyword in haystack for keyword in ["form", "submit", "submission"]):
        return "Form Submission Failure"

    return "General Issue"


def derive_bug_name(payload: dict) -> str:
    # Fallback priority:
    # 1) bug_name
    # 2) issue_type
    # 3) failed step name
    # 4) generated short title
    # 5) General Issue
    bug_name = _shorten(str(payload.get("bug_name") or "").strip(), 50)
    if bug_name:
        return bug_name

    issue_type = _normalize_issue_type(str(payload.get("issue_type") or ""))
    if issue_type:
        return issue_type

    failed_step_name = _shorten(
        str(
            payload.get("failed_step_name")
            or payload.get("failed_step")
            or payload.get("step_name")
            or payload.get("test")
            or payload.get("title")
            or ""
        ).strip(),
        50,
    )
    if failed_step_name:
        return failed_step_name

    generated = _classify_generated_title(
        str(payload.get("description") or ""),
        str(payload.get("bug_description") or ""),
        str(payload.get("details") or ""),
    )
    if generated in GENERIC_FALLBACKS or generated == "General Issue":
        return generated

    return "General Issue"


def normalize_bug_record(raw_bug: dict) -> dict:
    bug = dict(raw_bug or {})
    fallback_id = str(bug.get("_id") or "").strip()
    bug_id = str(bug.get("bug_id") or "").strip() or fallback_id
    bug_name = derive_bug_name(bug)
    bug_description = str(bug.get("bug_description") or bug.get("description") or "No details provided").strip()

    bug["bug_id"] = bug_id
    bug["bug_name"] = bug_name
    bug["title"] = bug_name
    bug["bug_description"] = bug_description
    bug["description"] = bug_description
    bug.pop("_id", None)
    return bug


def _format_validation_notes(validation: dict) -> str:
    notes = []
    console_errors = validation.get("console_errors") if isinstance(validation, dict) else []
    network_failures = validation.get("network_failures") if isinstance(validation, dict) else []

    if console_errors:
        notes.append(f"Console errors: {', '.join(str(item) for item in console_errors if item)}")
    if network_failures:
        notes.append(f"Network failures: {', '.join(str(item) for item in network_failures if item)}")

    return " | ".join(notes)


def _collect_bug_screenshots(test_data: dict, result: dict) -> list[str]:
    screenshots: list[str] = []
    for raw in [result.get("screenshot"), result.get("screenshot_path")]:
        if isinstance(raw, str) and raw.strip():
            screenshots.append(raw.strip())
    for raw in test_data.get("screenshot_paths", []) or []:
        if isinstance(raw, str) and raw.strip():
            screenshots.append(raw.strip())
    seen = set()
    ordered: list[str] = []
    for shot in screenshots:
        normalized = shot if shot.startswith("/") else f"/{shot.lstrip('/')}"
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _compute_bug_fingerprint(test_data: dict, result: dict) -> str:
    """Compute the canonical bug fingerprint for a legacy result record.

    Delegates to
    :func:`backend.services.execution_truth_engine.compute_bug_fingerprint`
    so all fingerprint values in the system use the same format. The
    previous SHA-256-based implementation produced a different string
    and has been removed; this shim keeps the call site stable for
    any historical caller that still passes raw ``test_data``/``result``
    dicts.
    """
    step = (
        result.get("step")
        if isinstance(result.get("step"), dict)
        else result.get("original_step")
        if isinstance(result.get("original_step"), dict)
        else {}
    )


def _severity_score(severity: str) -> int:
    return {
        "critical": 100,
        "high": 80,
        "medium": 55,
        "low": 30,
        "info": 10,
    }.get(str(severity or "").lower(), 45)


def _bug_intelligence_payload(*, severity: str, failure_category: str, root_cause: str | None, fingerprint: str, existing: dict | None = None) -> dict:
    occurrences = int((existing or {}).get("occurrences") or 0) + 1
    recurrence = "recurring" if occurrences > 1 else "new"
    confidence = 0.86 if root_cause else 0.68
    return {
        "severity_score": _severity_score(severity),
        "recurrence": recurrence,
        "occurrences": occurrences,
        "duplicate_key": fingerprint,
        "diagnosis_confidence": confidence,
        "triage_hint": (
            f"{failure_category or 'UNKNOWN'} failure with root cause {root_cause or 'UNKNOWN'}."
            " Re-run after fixing to verify lifecycle resolution."
        ),
    }
    step_index = (
        step.get("step_index")
        or step.get("index")
        or result.get("step_index")
    )
    step_name = str(
        result.get("test")
        or result.get("failed_step_name")
        or step.get("action")
        or step.get("name")
        or ""
    )
    scenario_id = str(
        result.get("scenario_id")
        or result.get("objective_id")
        or test_data.get("scenario_id")
        or ""
    )
    objective_id = str(result.get("objective_id") or test_data.get("objective_id") or "")
    return compute_bug_fingerprint(
        scenario_id=scenario_id,
        objective_id=objective_id,
        step_index=step_index,
        step_name=step_name,
    )


def _ensure_bug_indexes() -> None:
    try:
        bug_collection.create_index("fingerprint", unique=True, sparse=True)
        bug_collection.create_index([("user_id", 1), ("test_id", 1)])
        bug_collection.create_index([("user_id", 1), ("status", 1)])
    except Exception:
        pass


_ensure_bug_indexes()


def create_bugs_from_test(test_data):
    """Create bug records from the truth-engine ``bug_events`` only.

    This function no longer scans ``test_data["results"]`` for
    ``status == "fail"``. It only consumes the BUG_DETECTED events
    produced by ``execution_truth_engine.evaluate_test_run`` which is
    the single source of truth for what should be a bug. If a run did
    not emit any BUG_DETECTED event, this function is a no-op.
    """
    created_bugs = []
    now_iso = datetime.utcnow().isoformat()
    bug_events = test_data.get("bug_events") or []

    for event in bug_events:
        if not isinstance(event, dict):
            continue
        if event.get("type") != BUG_EVENT_DETECTED:
            continue

        fingerprint = str(event.get("fingerprint") or "").strip()
        if not fingerprint:
            continue

        failure_category = str(event.get("failure_category") or "").strip().upper()
        root_cause = str(event.get("root_cause") or "").strip().upper() or None
        severity = str(event.get("severity") or "medium").lower()
        step_name = str(event.get("step_name") or "").strip()
        step_index = event.get("step_index")
        error_text = str(event.get("error") or "").strip()
        bug_name = _shorten(step_name or "General Issue", 50)
        bug_description = error_text or "Step execution failure detected by truth engine."

        existing = bug_collection.find_one({"fingerprint": fingerprint})
        if existing:
            intelligence = _bug_intelligence_payload(
                severity=severity,
                failure_category=failure_category,
                root_cause=root_cause,
                fingerprint=fingerprint,
                existing=existing,
            )
            bug_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {"updated_at": now_iso, "last_seen_test_id": test_data.get("test_id"), "intelligence": intelligence}, "$inc": {"occurrences": 1}},
            )
            if not existing.get("bug_id"):
                bug_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"bug_id": str(uuid.uuid4())}},
                )
            bug = dict(existing)
            bug["intelligence"] = intelligence
            bug["occurrences"] = intelligence["occurrences"]
            bug.pop("_id", None)
            created_bugs.append(bug)
            continue

        intelligence = _bug_intelligence_payload(
            severity=severity,
            failure_category=failure_category,
            root_cause=root_cause,
            fingerprint=fingerprint,
        )
        bug = {
            "bug_id": str(uuid.uuid4()),
            "fingerprint": fingerprint,
            "test_id": test_data["test_id"],
            "execution_id": test_data.get("execution_id") or test_data["test_id"],
            "user_id": test_data["user_id"],
            "issue_type": "",
            "failed_step_name": step_name,
            "bug_name": bug_name,
            "title": bug_name,
            "bug_description": bug_description,
            "description": bug_description,
            "test_name": test_data.get("test_name") or test_data.get("project") or "",
            "severity": severity,
            "status": "open",
            "failure_category": failure_category,
            "root_cause": root_cause,
            "step_index": step_index,
            "evidence": {
                "failure_category": failure_category,
                "root_cause": root_cause,
                "step_index": step_index,
                "step_name": step_name,
                "error": error_text,
                "screenshots": _collect_bug_screenshots(test_data, {}),
            },
            "url": test_data.get("url") or "",
            "created_at": now_iso,
            "updated_at": now_iso,
            "occurrences": 1,
            "first_seen_test_id": test_data.get("test_id"),
            "last_seen_test_id": test_data.get("test_id"),
            "intelligence": intelligence,
        }

        try:
            bug_collection.insert_one(bug)
        except Exception:
            existing = bug_collection.find_one({"fingerprint": fingerprint})
            if existing:
                bug.pop("_id", None)
                bug = dict(existing)
                bug.pop("_id", None)

        created_bugs.append(bug)

    return created_bugs
