from playwright.sync_api import sync_playwright


def run_test(url: str):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # ---- Test 1: Page Load ----
        try:
            page.goto(url, timeout=10000)

            results.append({
                "test": "Page Load",
                "status": "pass"
            })

        except Exception as e:
            results.append({
                "test": "Page Load",
                "status": "fail",
                "error": str(e)
            })

            browser.close()
            return results  # stop further tests if page fails

        # ---- Test 2: Title Check ----
        try:
            title = page.title()

            if title and len(title) > 0:
                results.append({
                    "test": "Check Title",
                    "status": "pass",
                    "details": title
                })
            else:
                results.append({
                    "test": "Check Title",
                    "status": "fail",
                    "error": "Title is empty"
                })

        except Exception as e:
            results.append({
                "test": "Check Title",
                "status": "fail",
                "error": str(e)
            })

        browser.close()

    return results