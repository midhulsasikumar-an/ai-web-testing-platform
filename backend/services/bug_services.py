import uuid
from datetime import datetime
from backend.database.mongo import bug_collection


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


def create_bugs_from_test(test_data):
    created_bugs = []

    for result in test_data.get("results", []):

        if result["status"] == "fail":

            bug_name = derive_bug_name(result)
            bug_description = str(result.get("details", "No details provided") or "No details provided").strip()

            bug = {
                "bug_id": str(uuid.uuid4()),

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

                "url": test_data["url"],

                "created_at": datetime.utcnow().isoformat()
            }

            bug_collection.insert_one(bug)

            created_bugs.append(bug)

    return created_bugs