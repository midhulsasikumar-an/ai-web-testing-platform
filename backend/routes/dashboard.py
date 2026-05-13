from fastapi import APIRouter
from backend.database.mongo import collection
from backend.services.ai_log_service import generate_ai_logs
from collections import defaultdict


router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats():

    tests = list(collection.find({
        "user_id": "demo-user"
    }))

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
        insights = test.get("insights", {})

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

    return {
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "open_bugs": warnings,
        "average_health": average_health,
        "test_activity": test_activity,
        "bug_distribution": {
            "critical": critical_count,
            "moderate": moderate_count,
            "minor": minor_count
        },
        "ai_logs": ai_logs,
    }