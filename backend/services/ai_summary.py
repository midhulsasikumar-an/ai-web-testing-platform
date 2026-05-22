def generate_summary_line(score, summary, insights):
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)

    critical_count = len(insights.get("critical", []))
    moderate_count = len(insights.get("moderate", []))

    # Base summary
    if score >= 85:
        base = "The website is well-optimized and performs reliably."
    elif score >= 60:
        base = "The website is functional but has areas that need improvement."
    else:
        base = "The website has significant issues affecting usability and performance."

    # Context
    if critical_count > 0:
        detail = f" {critical_count} critical issue(s) require immediate attention."
    elif moderate_count > 0:
        detail = f" {moderate_count} moderate issue(s) were identified and should be addressed."
    elif failed == 0:
        detail = " All tests passed successfully."
    else:
        detail = f" {failed} test(s) failed and should be reviewed."

    return (base + detail).strip()
