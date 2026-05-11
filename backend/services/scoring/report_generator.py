def generate_report(score, summary, insights):
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)

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