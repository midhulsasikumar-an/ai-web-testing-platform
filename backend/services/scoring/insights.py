from backend.services.failure_classifier import collect_failure_category_counts, format_failure_category_insight


def generate_insights(results):
    critical = []
    moderate = []
    minor = []
    console_errors = []
    network_failures = []
    failure_category_counts = collect_failure_category_counts(results)

    for r in results:
        test = r.get("test", "")
        status = r.get("status", "")
        details = r.get("details", "")
        validation = r.get("validation") if isinstance(r.get("validation"), dict) else {}
        console_errors.extend(str(item) for item in validation.get("console_errors", []) if item)
        network_failures.extend(str(item) for item in validation.get("network_failures", []) if item)

        if status == "fail":
            if "Error Page" in test:
                critical.append("The page appears to be broken or not found, which is a critical issue.")
            
            elif "Page Load" in test:
                critical.append("The page failed to load properly, affecting accessibility.")

            elif "Links" in test:
                moderate.append(f"{details} detected, which may negatively impact user navigation and SEO performance.")

            elif "Console" in test:
                moderate.append("JavaScript console errors detected, which may break functionality.")

            elif "Performance" in test:
                moderate.append("Slow loading performance detected, which may impact user experience.")

            else:
                minor.append(f"Issue detected in {test}.")

        elif status == "info":
            if "Input" in test:
                minor.append("No input fields found. This may limit user interaction if forms are expected.")

            elif "Button" in test:
                minor.append("Limited interactive elements detected on the page.")

    if console_errors:
        moderate.append(
            f"Browser console errors may indicate frontend runtime issues. {len(console_errors)} console error(s) were detected during execution."
        )

    if network_failures:
        moderate.append(
            f"Network request failures were detected during testing. {len(network_failures)} failed network request(s) were observed."
        )

    for category, count in failure_category_counts.items():
        if category == "UNKNOWN":
            continue
        moderate.append(format_failure_category_insight(category, count))

    return {
        "critical": list(set(critical)),
        "moderate": list(set(moderate)),
        "minor": list(set(minor))
    }