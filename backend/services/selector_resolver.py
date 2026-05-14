def resolve_selector(target: str, dom_data: dict):

    target_lower = target.lower().strip()

    # ==========================================
    # 1. INPUTS (Highest Priority)
    # ==========================================
    for input_el in dom_data.get("inputs", []):

        name = (input_el.get("name") or "").lower().strip()
        placeholder = (input_el.get("placeholder") or "").lower().strip()

        # EXACT MATCHES FIRST
        if target_lower == name or target_lower == placeholder:

            # data-testid
            if input_el.get("data_testid"):
                return f'[data-testid="{input_el["data_testid"]}"]'

            # id
            if input_el.get("id"):
                return f'#{input_el["id"]}'

            # name
            if input_el.get("name"):
                return f'[name="{input_el["name"]}"]'

    # ==========================================
    # 2. BUTTONS
    # ==========================================
    for btn in dom_data.get("buttons", []):

        text = (btn.get("text") or "").lower().strip()
        aria = (btn.get("aria_label") or "").lower().strip()

        # EXACT MATCHES FIRST
        if target_lower == text or target_lower == aria:

            # BEST → data-testid
            if btn.get("data_testid"):
                return f'[data-testid="{btn["data_testid"]}"]'

            # BEST → id
            if btn.get("id"):
                return f'#{btn["id"]}'

            # BETTER → aria-label
            if btn.get("aria_label"):
                return f'[aria-label="{btn["aria_label"]}"]'

            # BETTER → stable class
            if btn.get("class"):
                first_class = btn["class"].split()[0]

                # avoid garbage utility classes
                if len(first_class) > 3:
                    return f'.{first_class}'

            # LAST → exact text
            if btn.get("text"):
                return f'text="{btn["text"]}"'

    # ==========================================
    # 3. LINKS
    # ==========================================
    for link in dom_data.get("links", []):

        text = (link.get("text") or "").lower().strip()

        if target_lower == text:

            return f'text="{link["text"]}"'

    # ==========================================
    # 4. PARTIAL MATCH FALLBACK
    # ==========================================
    for btn in dom_data.get("buttons", []):

        text = (btn.get("text") or "").lower()

        if target_lower in text:

            if btn.get("id"):
                return f'#{btn["id"]}'

            return f'text="{btn["text"]}"'

    # ==========================================
    # 5. FINAL FALLBACK
    # ==========================================
    return f'text="{target}"'