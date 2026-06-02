from collections import defaultdict

from fastapi import APIRouter, Depends

from backend.database.mongo import bug_collection, collection
from backend.services.ai_log_service import generate_ai_logs
from backend.services.auth import get_current_user


router = APIRouter()


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
        key=lambda x: str(x.get("created_at", "")),
        reverse=True
    )

    for test in sorted_tests[:5]:
        recent_tests.append({
            "test_id": str(test.get("test_id") or test.get("_id", "")),
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