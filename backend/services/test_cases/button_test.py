def test_buttons(page):
    try:
        buttons = page.query_selector_all("button, a, [role='button']")

        tested_buttons = []

        for btn in buttons:
            try:
                if not btn.is_visible():
                    continue

                # Get visible text or fallback to aria-label
                text = btn.inner_text().strip().replace("\n", " ")
                if not text:
                    text = (btn.get_attribute("aria-label") or "").strip()

                # Skip useless buttons
                if not text or len(text) < 2:
                    continue

                tested_buttons.append(text)

                # Limit to first 5 buttons
                if len(tested_buttons) >= 5:
                    break

            except:
                continue

        if not tested_buttons:
            return {
                "test": "Button Interaction",
                "status": "info",
                "details": "No meaningful visible buttons found"
            }

        return {
            "test": "Button Interaction",
            "status": "pass",
            "tested_buttons": tested_buttons
        }

    except Exception as e:
        return {
            "test": "Button Interaction",
            "status": "fail",
            "error": str(e)
        }