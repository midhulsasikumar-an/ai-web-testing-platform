def test_error_page(page, folder_path, test_id, screenshots):
    try:
        title = page.title().lower().strip()
        url = page.url.lower().strip()

        # Get visible body text safely
        try:
            body_text = page.locator("body").inner_text().lower()
        except:
            body_text = ""

        matches = []

        # ---------------------------------------------------
        # 1. HTTP STATUS CHECK (MOST IMPORTANT)
        # ---------------------------------------------------

        response = page.goto(page.url, wait_until="domcontentloaded")

        if response:
            status_code = response.status

            if status_code >= 400:
                matches.append(f"http {status_code}")

        # ---------------------------------------------------
        # 2. TITLE CHECKS
        # ---------------------------------------------------

        title_signals = [
            "404",
            "not found",
            "access denied",
            "page unavailable",
            "error"
        ]

        for signal in title_signals:
            if signal in title:
                matches.append(f"title:{signal}")

        # ---------------------------------------------------
        # 3. STRONG BODY TEXT CHECKS
        # ---------------------------------------------------

        body_signals = [
            "page not found",
            "this page does not exist",
            "requested url was not found",
            "access denied",
            "you don't have permission",
            "the page you are looking for",
            "error 404"
        ]

        for signal in body_signals:
            if signal in body_text:
                matches.append(f"body:{signal}")

        # Remove duplicates
        matches = list(set(matches))

        # ---------------------------------------------------
        # FAIL ONLY IF REAL SIGNALS EXIST
        # ---------------------------------------------------

        if matches:

            error_path = f"{folder_path}/error.png"

            page.screenshot(path=error_path)

            screenshots["error"] = (
                f"/screenshots/{test_id}/error.png"
            )

            return {
                "test": "Error Page Detection",
                "status": "fail",
                "error": f"Detected error indicators: {', '.join(matches)}"
            }

        return {
            "test": "Error Page Detection",
            "status": "pass"
        }

    except Exception as e:
        return {
            "test": "Error Page Detection",
            "status": "fail",
            "error": str(e)
        }