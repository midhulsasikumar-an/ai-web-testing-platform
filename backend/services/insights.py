def generate_insights(results):
    critical = []
    moderate = []
    minor = []

    for r in results:
        test = r.get("test", "")
        status = r.get("status", "")
        details = r.get("details", "")

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

    return {
        "critical": list(set(critical)),
        "moderate": list(set(moderate)),
        "minor": list(set(minor))
    }
