from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from backend.database.mongo import bug_collection, collection
from backend.services.ai_log_service import generate_ai_logs
from backend.services.auth import get_current_user


router = APIRouter()


# Sentinel value used as the sort key for any test_run record whose
# created_at is missing or unparseable. Picking an explicit value (rather
# than the empty string the old code used) means a record with a missing
# timestamp always sorts to the BOTTOM of "latest" lists, never the top.
_OLDEST_KNOWN_TIMESTAMP = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _parse_created_at(value) -> datetime:
    """Parse a created_at value (str / datetime / None) into an aware datetime.

    Returns the sentinel _OLDEST_KNOWN_TIMESTAMP when the value is missing or
    unparseable so the record always sorts to the bottom of a latest-first
    ordering. The previous string-sort implementation put empty strings at
    the END of the list (i.e. appearing "latest"), which is the opposite of
    the desired behavior.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not value:
        return _OLDEST_KNOWN_TIMESTAMP
    text = str(value).strip()
    if not text:
        return _OLDEST_KNOWN_TIMESTAMP
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return _OLDEST_KNOWN_TIMESTAMP
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _recent_tests_sort_key(test: dict) -> tuple:
    """Sort key: (created_at DESC, test_id DESC).

    We use a tuple so the second key (test_id) provides a deterministic
    tie-breaker for runs that share a created_at string. Sorting on raw
    ISO strings already produces correct chronological order for well-formed
    input, but the test_id tie-breaker keeps order stable across calls and
    across any caching layers that snapshot the result.
    """
    created_at = _parse_created_at(test.get("created_at"))
    test_id = str(test.get("test_id") or test.get("_id") or "")
    # Negate via reverse=True at the call site, so we just return ascending values.
    return (created_at, test_id)


def _derive_risk_level(total_tests: int, failed: int, average_health: int, open_bugs: int) -> str:
    """Compute risk level from real metrics, returning one of low/medium/high/unknown."""
    if total_tests == 0:
        return "unknown"

    fail_rate = failed / total_tests if total_tests else 0

    if fail_rate >= 0.4 or average_health < 60 or open_bugs >= 10:
        return "high"
    if fail_rate >= 0.2 or average_health < 80 or open_bugs >= 3:
        return "medium"
    return "low"


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    projection = {
        "overall_status": 1,
        "health_score": 1,
        "created_at": 1,
        "insights": 1,
        "test_id": 1,
        "test_name": 1,
        "name": 1,
        "project": 1,
        "url": 1,
        "test_type": 1,
        "results": 1,
    }

    tests = list(collection.find({"user_id": current_user["user_id"]}, projection))

    total_tests = len(tests)

    passed = len([
        t for t in tests
        if t.get("overall_status") == "pass"
    ])

    failed = len([
        t for t in tests
        if t.get("overall_status") == "fail"
    ])

    warnings = len([
        t for t in tests
        if t.get("overall_status") == "warning"
    ])

    health_scores = [
        t.get("health_score", 0)
        for t in tests
        if t.get("health_score") is not None
    ]

    average_health = (
        round(sum(health_scores) / len(health_scores))
        if health_scores
        else 0
    )

    try:
        open_bugs = bug_collection.count_documents({
            "user_id": current_user["user_id"],
            "status": {"$in": ["open", "in-progress", "Open", "In Progress"]},
        })
    except Exception:
        open_bugs = warnings

    risk_level = _derive_risk_level(total_tests, failed, average_health, open_bugs)

    activity_map = defaultdict(lambda: {
        "passed": 0,
        "failed": 0
    })

    try:
        for test in tests:
            created_at = test.get("created_at")

            if not created_at or not isinstance(created_at, str):
                continue

            day = created_at[:10]

            status = test.get("overall_status")

            if status == "pass":
                activity_map[day]["passed"] += 1

            elif status == "fail":
                activity_map[day]["failed"] += 1
    except Exception as e:
        print("Activity processing error:", e)

    test_activity = sorted(
        [
            {
                "day": day,
                "passed": values["passed"],
                "failed": values["failed"]
            }
            for day, values in activity_map.items()
        ],
        key=lambda x: x["day"]
    )[-7:]

    critical_count = 0
    moderate_count = 0
    minor_count = 0
    for test in tests:
        insights = test.get("insights") or {}

        critical_count += len(insights.get("critical", []))
        moderate_count += len(insights.get("moderate", []))
        minor_count += len(insights.get("minor", []))

    ai_logs = generate_ai_logs(
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        warnings=warnings,
        average_health=average_health
    )

    recent_tests = []

    sorted_tests = sorted(
        tests,
        key=_recent_tests_sort_key,
        reverse=True,
    )

    for test in sorted_tests[:5]:
        recent_tests.append({
            "test_id": str(test.get("test_id") or test.get("_id", "")),
            "test_name": test.get("test_name") or test.get("name") or test.get("project") or "",
            "project": test.get("project", "Unknown"),
            "url": test.get("url", ""),
            "overall_status": test.get("overall_status", "unknown"),
            "health_score": test.get("health_score", 0),
            "test_type": test.get("test_type", "full"),
            "date": str(test.get("created_at", ""))[:10]
        })

    return {
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "open_bugs": open_bugs,
        "average_health": average_health,
        "test_activity": test_activity,
        "bug_distribution": {
            "critical": critical_count,
            "moderate": moderate_count,
            "minor": minor_count
        },
        "ai_logs": ai_logs,
        "ai_summary": {
            "summary": (
                f"{passed}/{total_tests} tests passing, {open_bugs} open bug(s) tracked."
                if total_tests > 0
                else "No tests recorded yet."
            ),
            "insights": [
                f"{critical_count} critical finding(s) across all runs.",
                f"{failed} failed test(s) in the active dataset.",
            ] if total_tests > 0 else [],
            "risk_level": risk_level,
        },
        "recent_tests": recent_tests,
    }