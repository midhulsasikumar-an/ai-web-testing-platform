def generate_recommendations(insights):
    recommendations = []

    for issue in insights.get("critical", []):
        issue_lower = issue.lower()

        if "not found" in issue_lower or "broken" in issue_lower:
            recommendations.append(
                "Ensure all routes and pages are correctly configured and accessible to avoid broken experiences."
            )

        if "failed to load" in issue_lower:
            recommendations.append(
                "Check server health, API dependencies, and network issues to ensure the page loads reliably."
            )

    for issue in insights.get("moderate", []):
        issue_lower = issue.lower()

        if "broken links" in issue_lower:
            recommendations.append(
                "Fix or remove broken links to improve navigation, user trust, and search engine rankings."
            )

        if "console errors" in issue_lower:
            recommendations.append(
                "Resolve JavaScript console errors to prevent unexpected behavior and improve stability."
            )

        if "slow loading performance" in issue_lower:
            recommendations.append(
                "Optimize images, scripts, and backend response time to improve loading speed and performance."
            )

    for issue in insights.get("minor", []):
        issue_lower = issue.lower()

        if "input" in issue_lower:
            recommendations.append(
                "Consider adding relevant input fields or forms to enhance user interaction if applicable."
            )

        if "interactive" in issue_lower:
            recommendations.append(
                "Improve user engagement by adding clear buttons or call-to-action elements."
            )

    return list(set(recommendations))