def test_buttons(page, folder_path, test_id, screenshots):
    try:
        buttons = page.query_selector_all(
            "button, input[type='submit'], input[type='button'], [role='button']"
        )
        dangerous = ["logout", "delete", "remove"]
        
        tested_buttons = []

        interaction_count = 1

        for btn in buttons:
            try:
                if not btn.is_visible():
                    continue

                text = btn.inner_text().strip().replace("\n", " ")

                if not text:
                    text = (btn.get_attribute("aria-label") or "").strip()

                if not text or len(text) < 2:
                    continue

                if text.lower() in dangerous:
                    continue

                tested_buttons.append(text)

                # --- REAL INTERACTION ---
                btn.click(force=True, timeout=3000)

                try:
                    page.wait_for_load_state("networkidle", timeout=1000)
                except Exception:
                    page.wait_for_timeout(250)

                # --- SCREENSHOT AFTER INTERACTION ---
                screenshot_path = (
                    f"{folder_path}/button_interaction{interaction_count}.png"
                )

                page.screenshot(path=screenshot_path)

                screenshots["button_interactions"].append(
                    f"/screenshots/{test_id}/button_interaction{interaction_count}.png"
                )

                interaction_count += 1

                # limit to 5
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
