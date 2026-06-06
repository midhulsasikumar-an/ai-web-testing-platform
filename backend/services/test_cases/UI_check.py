def test_critical_elements(page):
    try:
        selectors = [
            "nav",
            "header",
            "[role='navigation']",
            "[class*=nav i]",
            "[class*=menu i]",
            "[class*=header i]"
        ]

        # Step 1: Direct match
        for sel in selectors:
            if page.query_selector(sel):
                return {
                    "test": "Critical Elements",
                    "status": "pass"
                }

        # Step 2: Fallback → detect top bar layout
        elements = page.query_selector_all("div")

        for el in elements[:20]:  # check top elements only
            text = el.inner_text().lower()

            if "home" in text or "login" in text or "sign" in text:
                return {
                    "test": "Critical Elements",
                    "status": "pass",
                    "details": "Navigation-like structure detected"
                }

        return {
            "test": "Critical Elements",
            "status": "info",
            "details": "No clear navigation element found"
        }

    except Exception as e:
        return {"test": "Critical Elements", "status": "fail", "error": str(e)}