from backend.services.failure_classifier import format_failure_category_summary


def generate_summary_line(score, summary, insights, failure_category_counts=None):
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    recoveries_attempted = int(summary.get("recoveries_attempted", 0) or 0)
    recoveries_successful = int(summary.get("recoveries_successful", 0) or 0)
    steps_saved_by_recovery = int(summary.get("steps_saved_by_recovery", 0) or 0)
    objective_pass_rate = float(summary.get("objective_pass_rate", 0) or 0)
    scenario_pass_rate = float(summary.get("scenario_pass_rate", 0) or 0)
    critical_objective_failures = int(summary.get("critical_objective_failures", 0) or 0)

    critical_count = len(insights.get("critical", []))
    moderate_count = len(insights.get("moderate", []))
    console_messages = [issue for issue in insights.get("moderate", []) if "console error" in issue.lower()]
    network_messages = [issue for issue in insights.get("moderate", []) if "network request failure" in issue.lower() or "failed network request" in issue.lower()]

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

    diagnostics = []
    if console_messages:
        diagnostics.append(f" {console_messages[0]}")
    if network_messages:
        diagnostics.append(f" {network_messages[0]}")

    if failure_category_counts:
        top_category, top_count = max(failure_category_counts.items(), key=lambda item: item[1], default=("UNKNOWN", 0))
        if top_count > 0:
            diagnostics.append(f" {format_failure_category_summary(top_category)}")

    if recoveries_attempted or recoveries_successful or steps_saved_by_recovery:
        diagnostics.append(
            f" Recovery attempts: {recoveries_attempted}, successful: {recoveries_successful}, steps saved: {steps_saved_by_recovery}."
        )

    if objective_pass_rate or scenario_pass_rate or critical_objective_failures:
        diagnostics.append(
            f" Objectives passed: {objective_pass_rate:.0%}, scenarios passed: {scenario_pass_rate:.0%}, critical objective failures: {critical_objective_failures}."
        )

    return (base + detail + "".join(diagnostics)).strip()