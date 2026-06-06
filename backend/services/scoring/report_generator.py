def generate_report(score, summary, insights):
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    recoveries_attempted = int(summary.get("recoveries_attempted", 0) or 0)
    recoveries_successful = int(summary.get("recoveries_successful", 0) or 0)
    steps_saved_by_recovery = int(summary.get("steps_saved_by_recovery", 0) or 0)
    objective_pass_rate = float(summary.get("objective_pass_rate", 0) or 0)
    scenario_pass_rate = float(summary.get("scenario_pass_rate", 0) or 0)
    critical_objective_failures = int(summary.get("critical_objective_failures", 0) or 0)
    console_issues = [issue for issue in insights.get("moderate", []) if "console error" in issue.lower()]
    network_issues = [issue for issue in insights.get("moderate", []) if "network request failure" in issue.lower() or "failed network request" in issue.lower()]

    # Overall condition
    if score >= 80:
        condition = "in excellent condition with only minor improvements needed"
    elif score >= 50:
        condition = "functional but has noticeable issues that should be addressed"
    else:
        condition = "facing significant issues that impact usability and reliability"

    report = f"""
Website Analysis Report

Overall Health Score: {score}/100

The website is {condition}.
Out of {total} tests, {passed} passed and {failed} failed.
"""

    if objective_pass_rate or scenario_pass_rate or critical_objective_failures:
        report += (
            f"\nObjective Coverage:\n"
            f"- Objective pass rate: {objective_pass_rate:.0%}\n"
            f"- Scenario pass rate: {scenario_pass_rate:.0%}\n"
            f"- Critical objective failures: {critical_objective_failures}\n"
        )

    if recoveries_attempted or recoveries_successful or steps_saved_by_recovery:
        report += (
            f"\nRecovery Actions:\n"
            f"- Attempted: {recoveries_attempted}\n"
            f"- Successful: {recoveries_successful}\n"
            f"- Steps saved: {steps_saved_by_recovery}\n"
        )

    # --- Issues ---
    if insights["critical"]:
        report += "\nCritical Issues:\n"
        for i in insights["critical"]:
            report += f"- {i}\n"
    
    if not insights["critical"]:
        report += "\nNo critical issues detected.\n"

    if insights["moderate"]:
        report += "\nModerate Issues:\n"
        for i in insights["moderate"]:
            report += f"- {i}\n"

    if insights["minor"]:
        report += "\nMinor Observations:\n"
        for i in insights["minor"]:
            report += f"- {i}\n"

    if console_issues or network_issues:
        report += "\nExecution Diagnostics:\n"
        if console_issues:
            report += f"- {console_issues[0]}\n"
        if network_issues:
            report += f"- {network_issues[0]}\n"

    # --- Strengths ---
    report += "\nStrengths:\n"

    if passed > failed:
        report += "- Most core functionalities are working correctly.\n"

    if score >= 80:
        report += "- The website demonstrates strong performance and stability.\n"

    # --- Conclusion ---
    report += "\nConclusion:\n"

    if score >= 80:
        report += "The website is well-optimized, with only minor improvements required.\n"
    elif score >= 50:
        report += "The website is usable but requires improvements in key areas.\n"
    else:
        report += "The website needs significant fixes to improve functionality and user experience.\n"

    report += "\nImproving the highlighted areas will enhance overall usability, performance, and reliability."

    return report.strip()