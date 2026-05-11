from backend.services.scoring.severity_map import TEST_SEVERITY

def calculate_overall_status(results, insights, health_score):

    has_critical_ai_issue = len(insights.get("critical", [])) > 0

    has_critical_test_fail = any(
        r["status"] == "fail" and TEST_SEVERITY.get(r["test"], "minor") == "critical"
        for r in results
    )

    has_any_fail = any(r["status"] == "fail" for r in results)

    if has_critical_ai_issue or has_critical_test_fail:
        return "fail"

    if has_any_fail or health_score < 85:
        return "warning"

    return "pass"