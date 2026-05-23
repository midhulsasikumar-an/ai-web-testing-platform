def _normalize_phrase(text: str) -> str:
    normalized = (text or "").lower().strip().replace("_", " ")
    normalized = " ".join(normalized.split())
    normalized = normalized.replace("sign in", "login").replace("log in", "login")
    for prefix in ("input ", "field ", "textbox ", "button ", "label "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    for suffix in (" field", " input", " textbox", " box", " button"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
    return normalized


def _input_score(target_lower: str, input_el: dict) -> int:
    name = _normalize_phrase(input_el.get("name") or "")
    placeholder = _normalize_phrase(input_el.get("placeholder") or "")
    input_id = _normalize_phrase(input_el.get("id") or "")
    aria_label = _normalize_phrase(input_el.get("aria_label") or "")
    label = _normalize_phrase(input_el.get("label") or "")
    input_type = _normalize_phrase(input_el.get("type") or "")
    role = _normalize_phrase(input_el.get("role") or "")

    score = 0
    if target_lower == name or target_lower == placeholder or target_lower == input_id or target_lower == aria_label or target_lower == label:
        score += 100
    if target_lower in name or target_lower in placeholder or target_lower in input_id or target_lower in aria_label or target_lower in label:
        score += 60

    if any(keyword in target_lower for keyword in ["username", "user name", "email"]):
        if any(keyword in name or keyword in placeholder or keyword in input_id or keyword in aria_label or keyword in label for keyword in ["user", "email", "login"]):
            score += 40
        if input_type == "email":
            score += 20

    if "password" in target_lower:
        if "password" in name or "password" in placeholder or "password" in input_id or "password" in aria_label or "password" in label:
            score += 60
        if input_type == "password":
            score += 30

    if role == "textbox":
        score += 5

    return score


def resolve_selector(target: str, dom_data: dict):

    if not target:
        return None

    target_lower = _normalize_phrase(target)

    # =========================
    # 1. INPUTS (Highest Priority)
    # =========================
    for input_el in dom_data.get("inputs", []):

        name = _normalize_phrase(input_el.get("name") or "")
        placeholder = _normalize_phrase(input_el.get("placeholder") or "")
        input_id = _normalize_phrase(input_el.get("id") or "")
        aria_label = _normalize_phrase(input_el.get("aria_label") or "")
        label = _normalize_phrase(input_el.get("label") or "")
        input_type = _normalize_phrase(input_el.get("type") or "")
        role = _normalize_phrase(input_el.get("role") or "")

        # EXACT MATCH
        if target_lower == name or target_lower == placeholder or target_lower == aria_label or target_lower == label:

            if input_id:
                return f"#{input_id}"

            if input_el.get("name"):
                return f"[name='{input_el['name']}']"

            if input_el.get("aria_label"):
                return f'[aria-label="{input_el["aria_label"]}"]'

            if input_el.get("placeholder"):
                return f'input[placeholder="{input_el["placeholder"]}"]'

        # PARTIAL MATCH
        if target_lower in name or target_lower in placeholder or target_lower in aria_label or target_lower in label:

            if input_id:
                return f"#{input_id}"

            if input_el.get("name"):
                return f"[name='{input_el['name']}']"

            if input_el.get("aria_label"):
                return f'[aria-label="{input_el["aria_label"]}"]'

            if input_el.get("placeholder"):
                return f'input[placeholder="{input_el["placeholder"]}"]'

    # =========================
    # 2. BUTTONS
    # =========================

    exact_matches = []
    startswith_matches = []
    contains_matches = []

    for btn in dom_data.get("buttons", []):

        text = _normalize_phrase(btn.get("text") or "")
        aria = _normalize_phrase(btn.get("aria_label") or "")
        name = _normalize_phrase(btn.get("name") or "")
        button_id = _normalize_phrase(btn.get("id") or "")
        label = _normalize_phrase(btn.get("label") or "")
        role = _normalize_phrase(btn.get("role") or "")

        # ---------- EXACT ----------
        if target_lower == text or target_lower == aria or target_lower == name or target_lower == button_id or target_lower == label:
            exact_matches.append(btn)

        # ---------- STARTSWITH ----------
        elif text.startswith(target_lower) or aria.startswith(target_lower) or name.startswith(target_lower) or label.startswith(target_lower):
            startswith_matches.append(btn)

        # ---------- CONTAINS ----------
        elif target_lower in text or target_lower in aria or target_lower in name or target_lower in label:
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

        # 5. ROLE
        if btn.get("role"):
            return f'[role="{btn["role"]}"]'

        # 6. SUBMIT BUTTON
        if btn.get("type") == "submit":
            return 'button[type="submit"]'

        # 7. CLASS
        if btn.get("class"):
            first_class = btn["class"].split()[0]
            if first_class:
                return f".{first_class}"

        # 8. TEXT
        if btn.get("text"):
            return f'text="{btn["text"]}"'

    # =========================
    # 3. LINKS
    # =========================
    for link in dom_data.get("links", []):

        text = _normalize_phrase(link.get("text") or "")

        # EXACT MATCH
        if target_lower == text:
            return f'text="{link["text"]}"'

    for link in dom_data.get("links", []):

        text = _normalize_phrase(link.get("text") or "")

        # PARTIAL MATCH
        if target_lower in text:
            return f'text="{link["text"]}"'

    # =========================
    # 4. FINAL FALLBACK
    # =========================
    ranked_inputs = sorted(dom_data.get("inputs", []), key=lambda input_el: _input_score(target_lower, input_el), reverse=True)
    if ranked_inputs:
        best = ranked_inputs[0]
        if _input_score(target_lower, best) > 0:
            if best.get("id"):
                return f"#{best['id']}"
            if best.get("name"):
                return f"[name='{best['name']}']"
            if best.get("aria_label"):
                return f'[aria-label="{best["aria_label"]}"]'
            if best.get("placeholder"):
                return f'input[placeholder="{best["placeholder"]}"]'
            if best.get("type"):
                return f'input[type="{best["type"]}"]'

    if dom_data.get("inputs"):
        first_input = dom_data["inputs"][0]
        if first_input.get("placeholder"):
            return f'input[placeholder="{first_input["placeholder"]}"]'
        if first_input.get("id"):
            return f"#{first_input['id']}"
        if first_input.get("name"):
            return f"[name='{first_input['name']}']"
        if first_input.get("type"):
            return f'input[type="{first_input["type"]}"]'

    return f'text="{target}"'