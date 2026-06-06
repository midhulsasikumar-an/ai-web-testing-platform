from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlparse

from backend.database.mongo import selector_cache_collection

SAUCEDMO_SELECTOR_MAP = {
    "username": "#user-name",
    "username input": "#user-name",
    "user name": "#user-name",
    "password": "#password",
    "password input": "#password",
    "login": "#login-button",
    "login button": "#login-button",
    "sign in": "#login-button",
    "inventory": ".inventory_list",
    "inventory page": ".inventory_list",
    "cart page": ".cart_list",
    "cart link": ".shopping_cart_link",
    "cart badge": ".shopping_cart_badge",
    "add to cart": 'button[data-test*="add-to-cart"]',
    "checkout": "#checkout",
    "first name": "#first-name",
    "last name": "#last-name",
    "postal code": "#postal-code",
    "continue": "#continue",
    "finish": "#finish",
    "checkout complete": ".complete-header",
}

SELECTOR_CACHE_TTL_DAYS = 21


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


def _is_saucedemo_target(target_lower: str) -> bool:
    return target_lower in SAUCEDMO_SELECTOR_MAP


def _saucedemo_selector(target_lower: str) -> str | None:
    return SAUCEDMO_SELECTOR_MAP.get(target_lower)


def _looks_like_selector(selector: str) -> bool:
    normalized = (selector or "").strip()
    return any(token in normalized for token in ["#", ".", "[", "]", "=", "text="])


def _looks_like_semantic_only_target(text: str) -> bool:
    normalized = _normalize_phrase(text)
    return normalized in {
        "username input",
        "password input",
        "login button",
        "cart page",
        "cart badge",
        "cart link",
        "add to cart",
        "inventory page",
        "checkout complete",
    }


def _cache_domain(context: dict | None) -> str:
    context = context or {}
    for key in ("page_url", "url", "current_url"):
        value = str(context.get(key) or "").strip()
        if not value:
            continue
        try:
            parsed = urlparse(value)
            if parsed.hostname:
                return parsed.hostname.lower()
        except Exception:
            continue
    feature_key = str(context.get("feature_key") or context.get("objective_name") or context.get("scenario_name") or "").strip().lower()
    return feature_key or "global"


def _cache_page_type(context: dict | None, target_lower: str) -> str:
    context = context or {}
    values = [
        context.get("page_type"),
        context.get("feature_key"),
        context.get("objective_name"),
        context.get("scenario_name"),
        target_lower,
    ]
    for value in values:
        normalized = _normalize_phrase(str(value or ""))
        if normalized:
            return normalized.split()[0] if len(normalized.split()) > 1 else normalized
    return "global"


def _selector_cache_key(target_lower: str, context: dict | None, action: str | None) -> str:
    return "|".join([
        _cache_domain(context),
        _cache_page_type(context, target_lower),
        _normalize_phrase(target_lower),
        _normalize_phrase(action or ""),
    ])


def _lookup_selector_cache(target_lower: str, context: dict | None, action: str | None) -> dict | None:
    cache_key = _selector_cache_key(target_lower, context, action)
    ttl_floor = datetime.utcnow() - timedelta(days=SELECTOR_CACHE_TTL_DAYS)
    try:
        doc = selector_cache_collection.find_one(
            {
                "cache_key": cache_key,
                "$and": [
                    {
                        "$or": [
                            {"expires_at": {"$exists": False}},
                            {"expires_at": {"$gt": datetime.utcnow()}},
                        ]
                    },
                    {
                        "$or": [
                            {"last_success_at": {"$exists": False}},
                            {"last_success_at": {"$gte": ttl_floor}},
                        ]
                    },
                ],
            },
            sort=[("confidence", -1), ("hit_count", -1), ("last_success_at", -1)],
        )
    except Exception:
        return None
    return doc


def record_selector_success(selector: str, target: str, *, context: dict | None = None, action: str | None = None, source: str = "runtime") -> None:
    selector = str(selector or "").strip()
    if not selector:
        return

    cache_key = _selector_cache_key(_normalize_phrase(target), context, action)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=SELECTOR_CACHE_TTL_DAYS)
    try:
        selector_cache_collection.update_one(
            {"cache_key": cache_key, "selector": selector},
            {
                "$set": {
                    "cache_key": cache_key,
                    "selector": selector,
                    "target": str(target or ""),
                    "action": _normalize_phrase(action or ""),
                    "domain": _cache_domain(context),
                    "page_type": _cache_page_type(context, _normalize_phrase(target)),
                    "source": source,
                    "last_success_at": now,
                    "expires_at": expires_at,
                },
                "$setOnInsert": {"created_at": now, "miss_count": 0},
                "$inc": {"hit_count": 1},
            },
            upsert=True,
        )
    except Exception as e:
        return


def resolve_selector(target: str, dom_data: dict, *, context: dict | None = None):

    # Returns a dict with diagnostics and selector candidate info.
    # { "selector": str|None, "source": str, "candidates": [..], "unresolved": bool }

    if not target:
        return {"selector": None, "source": "", "candidates": [], "unresolved": True}

    target_lower = _normalize_phrase(target)
    candidates = []
    cache_doc = _lookup_selector_cache(target_lower, context, context.get("action") if isinstance(context, dict) else None)
    if cache_doc and cache_doc.get("selector"):
        return {
            "selector": cache_doc.get("selector"),
            "source": "cache",
            "candidates": [{"selector": cache_doc.get("selector"), "source": "cache"}],
            "unresolved": False,
            "cache_hit": True,
            "confidence": float(cache_doc.get("confidence") or 0.85),
        }

    def add_candidate(sel, src):
        if not sel:
            return
        candidates.append({"selector": sel, "source": src})

    sauce_selector = _saucedemo_selector(target_lower)
    if sauce_selector:
        add_candidate(sauce_selector, "saucedemo-map")

    # Helper to prefer id, data-testid, name, placeholder, aria-label, role, visible text
    # for inputs
    for input_el in dom_data.get("inputs", []):
        name = input_el.get("name")
        placeholder = input_el.get("placeholder")
        input_id = input_el.get("id")
        aria_label = input_el.get("aria_label")
        label = input_el.get("label")
        input_type = input_el.get("type")

        # priority checks (exact then partial)
        if target_lower == _normalize_phrase(input_id or "") or target_lower == _normalize_phrase(name or "") or target_lower == _normalize_phrase(placeholder or "") or target_lower == _normalize_phrase(aria_label or "") or target_lower == _normalize_phrase(label or ""):
            if input_id:
                add_candidate(f"#{input_id}", "id")
            if input_el.get("data_testid"):
                add_candidate(f'[data-testid="{input_el.get("data_testid")}"]', "data-testid")
            if name:
                add_candidate(f"input[name='{name}']", "name")
            if placeholder:
                add_candidate(f'input[placeholder="{placeholder}"]', "placeholder")
            if aria_label:
                add_candidate(f'[aria-label="{aria_label}"]', "aria-label")

        # partial matches
        if target_lower in _normalize_phrase(name or "") or target_lower in _normalize_phrase(placeholder or "") or target_lower in _normalize_phrase(aria_label or "") or target_lower in _normalize_phrase(label or ""):
            if input_id:
                add_candidate(f"#{input_id}", "id")
            if input_el.get("data_testid"):
                add_candidate(f'[data-testid="{input_el.get("data_testid")}"]', "data-testid")
            if name:
                add_candidate(f"input[name='{name}']", "name")
            if placeholder:
                add_candidate(f'input[placeholder="{placeholder}"]', "placeholder")
            if aria_label:
                add_candidate(f'[aria-label="{aria_label}"]', "aria-label")

    # Buttons
    for btn in dom_data.get("buttons", []):
        text = _normalize_phrase(btn.get("text") or "")
        aria = _normalize_phrase(btn.get("aria_label") or "")
        name = btn.get("name")
        button_id = btn.get("id")
        btn_data_testid = btn.get("data_testid") or btn.get("data_testid")
        role = btn.get("role")
        if target_lower == text or target_lower == aria or target_lower == _normalize_phrase(name or "") or target_lower == _normalize_phrase(button_id or ""):
            if button_id:
                add_candidate(f"#{button_id}", "id")
            if btn_data_testid:
                add_candidate(f'[data-testid="{btn_data_testid}"]', "data-testid")
            if name:
                add_candidate(f'[name="{name}"]', "name")
            if btn.get("aria_label"):
                add_candidate(f'[aria-label="{btn.get("aria_label")}"]', "aria-label")
            if role:
                add_candidate(f'[role="{role}"]', "role")
            if btn.get("type") == "submit":
                add_candidate('button[type="submit"]', "type")
            if btn.get("class"):
                first_class = (btn["class"] or "").split()[0]
                if first_class:
                    add_candidate(f'.{first_class}', "class")
            if btn.get("text"):
                add_candidate(f'text="{btn.get("text")}"', "text")

        elif target_lower in text or target_lower in aria or target_lower in _normalize_phrase(name or ""):
            if button_id:
                add_candidate(f"#{button_id}", "id")
            if btn_data_testid:
                add_candidate(f'[data-testid="{btn_data_testid}"]', "data-testid")
            if name:
                add_candidate(f'[name="{name}"]', "name")
            if btn.get("aria_label"):
                add_candidate(f'[aria-label="{btn.get("aria_label")}"]', "aria-label")
            if btn.get("type") == "submit":
                add_candidate('button[type="submit"]', "type")
            if btn.get("text"):
                add_candidate(f'text="{btn.get("text")}"', "text")

    # Fuzzy token matching for visible text (helps when exact normalization differs)
    if not candidates:
        target_tokens = [t for t in target_lower.split() if t]
        if target_tokens:
            for btn in dom_data.get("buttons", []):
                text = _normalize_phrase(btn.get("text") or "")
                if all(tok in text for tok in target_tokens):
                    # prioritize id/data-testid/name if available
                    if btn.get("id"):
                        add_candidate(f"#{btn.get('id')}", "id")
                    if btn.get("data_testid"):
                        add_candidate(f'[data-testid="{btn.get("data_testid")}"]', "data-testid")
                    if btn.get("text"):
                        add_candidate(f'text="{btn.get("text")}"', "text")
            # inventory-specific patterns
            for btn in dom_data.get("buttons", []):
                bid = (btn.get("id") or "")
                bclass = (btn.get("class") or "")
                if "add-to-cart" in bid or "add-to-cart" in bclass or "btn_inventory" in bclass:
                    if btn.get("id"):
                        add_candidate(f"#{btn.get('id')}", "id")
                    if btn.get("class"):
                        first_class = btn["class"].split()[0]
                        add_candidate(f".{first_class}", "class")

    # Links
    for link in dom_data.get("links", []):
        text = _normalize_phrase(link.get("text") or "")
        if target_lower == text or target_lower in text:
            add_candidate(f'text="{link.get("text")}"', "text")

    # Alternate auth candidates (hard-coded common mappings)
    auth_alternates = []
    if any(k in target_lower for k in ["username", "user name", "email", "user"]):
        auth_alternates = ["#user-name", "input[name=\"user-name\"]", "input[placeholder*=\"Username\"]", "input[name=\"user\"]"]
    if "password" in target_lower:
        auth_alternates = ["#password", "input[type=\"password\"]"]
    if any(k in target_lower for k in ["login", "sign in", "sign-in", "submit"]):
        auth_alternates = ["#login-button", "button[type=\"submit\"]", "#login"]

    # Add auth alternates only if they appear in DOM
    for alt in auth_alternates:
        # quick heuristic: check if any element in dom contains the id/name/placeholder/etc referenced
        try:
            if alt.startswith("#"):
                candidate_id = alt[1:]
                for b in dom_data.get("buttons", []) + dom_data.get("inputs", []):
                    if b.get("id") == candidate_id:
                        add_candidate(alt, "alt-id")
            elif alt.startswith('input['):
                add_candidate(alt, "alt-attr")
            else:
                add_candidate(alt, "alt")
        except Exception:
            continue

    # Remove duplicate candidate selectors preserving order
    seen = set()
    unique = []
    for c in candidates:
        sel = c.get("selector")
        if sel in seen:
            continue
        seen.add(sel)
        unique.append(c)

    # If we have a concrete selector, return the first in priority order.
    # Allow DOM text selectors (source == 'text') as a valid fallback, but never allow plain semantic hints.
    for c in unique:
        sel = c.get("selector")
        src = c.get("source")
        if not sel:
            continue
        # Reject plain semantic hints like 'username input', 'password input', 'login button'
        norm = _normalize_phrase(sel)
        if norm in {"username input", "password input", "login button", "username", "password", "login"}:
            continue
        # If it's a CSS/XPath-like selector or attribute selector, accept it
        if _looks_like_selector(sel):
            return {"selector": sel, "source": src, "candidates": unique, "unresolved": False, "cache_hit": False, "confidence": 0.7 if src == "saucedemo-map" else 0.6}
        # If it's a text locator coming from DOM text, accept it
        if sel.startswith('text="') and src == "text":
            return {"selector": sel, "source": src, "candidates": unique, "unresolved": False, "cache_hit": False, "confidence": 0.55}

    # No concrete selector found — return unresolved but include candidates for diagnostics
    return {"selector": None, "source": "unresolved", "candidates": unique, "unresolved": True, "cache_hit": False, "confidence": 0.0}