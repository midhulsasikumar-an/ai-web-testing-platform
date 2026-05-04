def test_error_page(page):
    try:
        title = page.title().lower()
        url = page.url.lower()
        body_text = page.inner_text("body").lower()

        error_signals = ["404", "not found", "page not found", "access denied"]

        matches = [
            signal for signal in error_signals
            if signal in title or signal in url or signal in body_text
        ]

        # Only fail if STRONG signals exist
        if matches:
            return {
                "test": "Error Page Detection",
                "status": "fail",
                "error": f"Detected error page indicators: {', '.join(matches)}"
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