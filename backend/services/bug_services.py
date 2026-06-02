import hashlib
import uuid
from datetime import datetime
from backend.database.mongo import bug_collection
from backend.services.failure_classifier import classify_failure_category
from backend.services.root_cause_classifier import classify_root_cause


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
    step = result.get("step") if isinstance(result.get("step"), dict) else result.get("original_step") if isinstance(result.get("original_step"), dict) else {}
    test_id = str(test_data.get("test_id") or "")
    user_id = str(test_data.get("user_id") or "")
    failed_step_name = str(result.get("test") or result.get("failed_step_name") or step.get("action") or step.get("name") or "")
    selector = str(result.get("selector_used") or step.get("selector") or step.get("target") or "")
    target = str(step.get("target") or step.get("text") or step.get("url") or "")
    error = str(result.get("error") or result.get("details") or "")[:500]
    failure_category = str(result.get("failure_category") or "")
    parts = [test_id, user_id, failed_step_name, selector, target, error, failure_category]
    digest = "|".join(part.strip().lower() for part in parts)
    return hashlib.sha256(digest.encode("utf-8")).hexdigest()


def _ensure_bug_indexes() -> None:
    try:
        bug_collection.create_index("fingerprint", unique=True, sparse=True)
        bug_collection.create_index([("user_id", 1), ("test_id", 1)])
        bug_collection.create_index([("user_id", 1), ("status", 1)])
    except Exception:
        pass


_ensure_bug_indexes()


def create_bugs_from_test(test_data):
    created_bugs = []
    now_iso = datetime.utcnow().isoformat()

    for result in test_data.get("results", []):

        if result.get("status") == "fail":

            bug_name = derive_bug_name(result)
            validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
            failure_category = str(result.get("failure_category") or "").strip().upper() or classify_failure_category(
                error_text=result.get("error") or result.get("details") or "",
                console_errors=validation.get("console_errors"),
                network_failures=validation.get("network_failures"),
                step_text=str(result.get("test") or ""),
                selector=str(result.get("selector_used") or ""),
                target=str(result.get("step", {}).get("target") if isinstance(result.get("step"), dict) else ""),
                test_name=str(test_data.get("test_name") or test_data.get("project") or ""),
                validation=validation,
            )
            root_cause = str(result.get("root_cause") or "").strip().upper()
            root_cause_confidence = result.get("root_cause_confidence")
            recovery_actions = result.get("recovery_actions") if isinstance(result.get("recovery_actions"), list) else []
            recovery_attempted = bool(result.get("recovery_attempted")) or bool(recovery_actions)
            recovery_success = bool(result.get("recovery_success"))
            recovery_type = str(result.get("recovery_type") or "").strip()
            original_step = result.get("original_step") if isinstance(result.get("original_step"), dict) else result.get("step") if isinstance(result.get("step"), dict) else None
            replan_history = result.get("replan_attempts") if isinstance(result.get("replan_attempts"), list) else []
            screenshots = _collect_bug_screenshots(test_data, result)
            if root_cause not in {"SELECTOR_CHANGED", "ELEMENT_NOT_VISIBLE", "ELEMENT_NOT_FOUND", "NAVIGATION_REDIRECT", "NETWORK_FAILURE", "API_FAILURE", "AUTHENTICATION_FAILURE", "TIMEOUT", "PAGE_CRASH", "JAVASCRIPT_ERROR", "UNKNOWN"}:
                root_cause_result = classify_root_cause(
                    action=str(result.get("test") or ""),
                    category=failure_category,
                    error=result.get("error") or result.get("details") or "",
                    console_errors=validation.get("console_errors"),
                    network_failures=validation.get("network_failures"),
                    selector_used=str(result.get("selector_used") or ""),
                    validation=validation,
                )
                root_cause = str(root_cause_result["root_cause"]).upper()
                root_cause_confidence = root_cause_result["confidence"]
            validation_notes = _format_validation_notes(validation)
            bug_description = str(result.get("details", "No details provided") or "No details provided").strip()
            if validation_notes:
                bug_description = f"{bug_description}\n{validation_notes}".strip()
            if recovery_attempted:
                recovery_note = f"Recovery attempted: {recovery_type or 'unspecified'}"
                if recovery_success:
                    recovery_note += " (successful)"
                if recovery_actions:
                    recovery_note += f" via {len(recovery_actions)} attempt(s)"
                bug_description = f"{bug_description}\n{recovery_note}".strip()

            fingerprint = _compute_bug_fingerprint(test_data, result)
            existing = bug_collection.find_one({"fingerprint": fingerprint})

            if existing:
                if not existing.get("bug_id"):
                    bug_collection.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {"bug_id": str(uuid.uuid4())}},
                    )
                bug = dict(existing)
                bug.pop("_id", None)
                created_bugs.append(bug)
                continue

            bug = {
                "bug_id": str(uuid.uuid4()),

                "fingerprint": fingerprint,

                "test_id": test_data["test_id"],

                "execution_id": test_data.get("execution_id") or test_data["test_id"],

                "user_id": test_data["user_id"],

                "issue_type": str(result.get("issue_type") or "").strip(),

                "failed_step_name": str(result.get("test") or "").strip(),

                "bug_name": bug_name,

                "title": bug_name,

                "bug_description": bug_description,

                "description": bug_description,

                "test_name": test_data.get("test_name") or test_data.get("project") or "",

                "severity": "medium",

                "status": "open",

                "failure_category": failure_category,
                "root_cause": root_cause,
                "root_cause_confidence": root_cause_confidence,
                "recovery_attempted": recovery_attempted,
                "recovery_type": recovery_type or None,
                "recovery_success": recovery_success,
                "recovery_actions": recovery_actions,
                "original_step": original_step,
                "replan_attempts": replan_history,
                "screenshots": screenshots,

                "url": test_data["url"],

                "evidence": {
                    "validation": validation,
                    "failure_category": failure_category,
                    "root_cause": root_cause,
                    "root_cause_confidence": root_cause_confidence,
                    "recovery_attempted": recovery_attempted,
                    "recovery_type": recovery_type or None,
                    "recovery_success": recovery_success,
                    "recovery_actions": recovery_actions,
                    "original_step": original_step,
                    "replan_attempts": replan_history,
                    "screenshots": screenshots,
                    "console_errors": list(validation.get("console_errors", [])) if isinstance(validation, dict) else [],
                    "network_failures": list(validation.get("network_failures", [])) if isinstance(validation, dict) else [],
                },

                "created_at": now_iso,
                "updated_at": now_iso,
                "occurrences": 1,
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