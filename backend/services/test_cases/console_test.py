def test_console_errors(page):
    errors = []

    def handle_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", handle_console)

    try:
        page.reload()
        try:
            page.wait_for_load_state("networkidle", timeout=1500)
        except Exception:
            page.wait_for_load_state("domcontentloaded", timeout=1000)

        return {
            "test": "Console Errors",
            "status": "fail" if errors else "pass",
            "details": errors[:3] if errors else "No console errors"     }

    except Exception as e:
        return {"test": "Console Errors", "status": "fail", "error": str(e)}
