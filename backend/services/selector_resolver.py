def resolve_selector(target: str, dom_data: dict):

    if not target:
        return None

    target_lower = target.lower().strip()

    # =========================
    # 1. INPUTS (Highest Priority)
    # =========================
    for input_el in dom_data.get("inputs", []):

        name = (input_el.get("name") or "").lower().strip()
        placeholder = (input_el.get("placeholder") or "").lower().strip()
        input_id = input_el.get("id") or ""
        input_type = (input_el.get("type") or "").lower().strip()

        # EXACT MATCH
        if target_lower == name or target_lower == placeholder:

            if input_id:
                return f"#{input_id}"

            if input_el.get("name"):
                return f"[name='{input_el['name']}']"

        # PARTIAL MATCH
        if target_lower in name or target_lower in placeholder:

            if input_id:
                return f"#{input_id}"

            if input_el.get("name"):
                return f"[name='{input_el['name']}']"

    # =========================
    # 2. BUTTONS
    # =========================

    exact_matches = []
    startswith_matches = []
    contains_matches = []

    for btn in dom_data.get("buttons", []):

        text = (btn.get("text") or "").lower().strip()
        aria = (btn.get("aria_label") or "").lower().strip()

        # ---------- EXACT ----------
        if target_lower == text or target_lower == aria:
            exact_matches.append(btn)

        # ---------- STARTSWITH ----------
        elif text.startswith(target_lower) or aria.startswith(target_lower):
            startswith_matches.append(btn)

        # ---------- CONTAINS ----------
        elif target_lower in text or target_lower in aria:
            contains_matches.append(btn)

    # PRIORITY ORDER
    ranked_buttons = (
        exact_matches +
        startswith_matches +
        contains_matches
    )

    for btn in ranked_buttons:

        # 1. ID (BEST)
        if btn.get("id"):
            return f"#{btn['id']}"

        # 2. DATA-TESTID
        if btn.get("data_testid"):
            return f'[data-testid="{btn["data_testid"]}"]'

        # 3. NAME
        if btn.get("name"):
            return f'[name="{btn["name"]}"]'

        # 4. ARIA LABEL
        if btn.get("aria_label"):
            return f'[aria-label="{btn["aria_label"]}"]'

        # 5. SUBMIT BUTTON
        if btn.get("type") == "submit":
            return 'button[type="submit"]'

        # 6. CLASS
        if btn.get("class"):
            first_class = btn["class"].split()[0]
            if first_class:
                return f".{first_class}"

        # 7. TEXT
        if btn.get("text"):
            return f'text="{btn["text"]}"'

    # =========================
    # 3. LINKS
    # =========================
    for link in dom_data.get("links", []):

        text = (link.get("text") or "").lower().strip()

        # EXACT MATCH
        if target_lower == text:
            return f'text="{link["text"]}"'

    for link in dom_data.get("links", []):

        text = (link.get("text") or "").lower().strip()

        # PARTIAL MATCH
        if target_lower in text:
            return f'text="{link["text"]}"'

    # =========================
    # 4. FINAL FALLBACK
    # =========================
    return f'text="{target}"'