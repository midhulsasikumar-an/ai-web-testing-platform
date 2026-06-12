import inspect
import logging
import asyncio
from time import perf_counter
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright
from backend.services.safety_service import is_same_domain
from backend.services.selector_resolver import record_selector_success, resolve_selector
from backend.services.validation_service import (
    check_expected_text,
    check_url_change,
    check_error_messages,
    get_page_snapshot,
    detect_success_state
)
import traceback
import os
import base64

from backend.services.failure_classifier import classify_failure_category
from backend.services.root_cause_classifier import classify_root_cause
from backend.agent.browser_session import BrowserSessionManager
from backend.services.asyncio_windows import ensure_windows_event_loop_policy

logger = logging.getLogger("services.execution")

DEFAULT_STEP_TIMEOUT_MS = 30000
DEFAULT_SELECTOR_TIMEOUT_MS = 2000
DEFAULT_NAVIGATION_TIMEOUT_MS = 45000
DEFAULT_SCREENSHOT_TIMEOUT_MS = 10000
DEFAULT_RETRY_TIMEOUT_MS = 5000
MAX_SELECTOR_RETRY_ATTEMPTS = 2


def _is_saucedemo_url(url: str) -> bool:
    lowered = (url or "").lower()
    return "saucedemo.com" in lowered


def _is_saucedemo_inventory_url(url: str) -> bool:
    lowered = (url or "").lower()
    return any(path in lowered for path in [
        "/inventory.html",
        "/cart.html",
        "/checkout-step-one.html",
        "/checkout-step-two.html",
        "/checkout-complete.html",
    ])


async def _timed_call(progress_callback, label: str, coro, *, timeout_ms: int, meta: dict | None = None):
    started = perf_counter()
    await _emit_progress(progress_callback, {
        "type": "timing",
        "phase": "start",
        "label": label,
        "meta": meta or {},
    })
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_ms / 1000)
        return result
    finally:
        elapsed_ms = round((perf_counter() - started) * 1000, 1)
        await _emit_progress(progress_callback, {
            "type": "timing",
            "phase": "end",
            "label": label,
            "elapsed_ms": elapsed_ms,
            "meta": meta or {},
        })

async def safe_click(page, selector, progress_callback=None):

    locator = page.locator(selector).first
    await _timed_call(progress_callback, f"click:attach:{selector}", locator.wait_for(state="attached", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    await _timed_call(progress_callback, f"click:scroll:{selector}", locator.scroll_into_view_if_needed(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    try:
        await _timed_call(progress_callback, f"click:visible:{selector}", locator.wait_for(state="visible", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    except Exception:
        pass

    try:
        if await locator.is_enabled():
            await _timed_call(progress_callback, f"click:action:{selector}", locator.click(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
            return
    except Exception:
        pass

    await _timed_call(progress_callback, f"click:force:{selector}", locator.click(force=True), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})


async def safe_fill(page, selector, value, progress_callback=None):
    locator = page.locator(selector)

    await _timed_call(progress_callback, f"fill:attach:{selector}", locator.wait_for(state="attached", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    await _timed_call(progress_callback, f"fill:scroll:{selector}", locator.scroll_into_view_if_needed(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})

    try:
        await _timed_call(progress_callback, f"fill:visible:{selector}", locator.wait_for(state="visible", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    except Exception:
        pass

    try:
        if await locator.is_visible() and await locator.is_enabled():
            await _timed_call(progress_callback, f"fill:action:{selector}", locator.fill(value), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
            return
    except Exception:
        pass

    try:
        await _timed_call(progress_callback, f"fill:click:{selector}", locator.click(force=True), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
        await _timed_call(progress_callback, f"fill:ctrl+a:{selector}", page.keyboard.press("Control+A"), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
        await _timed_call(progress_callback, f"fill:backspace:{selector}", page.keyboard.press("Backspace"), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
        await _timed_call(progress_callback, f"fill:type:{selector}", page.keyboard.type(value, delay=25), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
        return
    except Exception:
        pass

    await _timed_call(progress_callback, f"fill:focus:{selector}", locator.focus(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    await _timed_call(progress_callback, f"fill:type-fallback:{selector}", page.keyboard.type(value, delay=25), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})


async def safe_wait(page, selector, progress_callback=None):
    locator = page.locator(selector).first
    await _timed_call(progress_callback, f"wait:visible:{selector}", locator.wait_for(state="visible", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})


async def safe_hover(page, selector, progress_callback=None):
    locator = page.locator(selector).first
    await _timed_call(progress_callback, f"hover:visible:{selector}", locator.wait_for(state="visible", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    await _timed_call(progress_callback, f"hover:action:{selector}", locator.hover(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})


async def safe_select(page, selector, value, progress_callback=None):
    locator = page.locator(selector).first
    await _timed_call(progress_callback, f"select:visible:{selector}", locator.wait_for(state="visible", timeout=DEFAULT_SELECTOR_TIMEOUT_MS), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})
    await _timed_call(progress_callback, f"select:action:{selector}", locator.select_option(value=value), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"selector": selector})


async def _ensure_saucedemo_authenticated_landing(page, url: str, test_case, authenticated: bool, progress_callback=None):
    if not authenticated:
        return
    if not _is_saucedemo_url(url):
        return

    feature_key = (getattr(test_case, "feature_key", "") or "").upper()
    if feature_key == "AUTHENTICATION":
        return

    current_url = page.url
    if _is_saucedemo_inventory_url(current_url):
        return

    try:
        login_form_visible = await page.locator("#login-button").first.is_visible()
    except Exception:
        login_form_visible = False

    if login_form_visible or current_url.rstrip("/").endswith("saucedemo.com"):
        inventory_url = "https://www.saucedemo.com/inventory.html"
        await _emit_progress(progress_callback, {
            "type": "run_status",
            "message": "Authenticated SauceDemo session detected; redirecting to inventory page",
        })
        await _timed_call(
            progress_callback,
            f"goto:{inventory_url}:domcontentloaded",
            page.goto(inventory_url, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT_MS),
            timeout_ms=DEFAULT_NAVIGATION_TIMEOUT_MS,
            meta={"url": inventory_url},
        )


def _distinct_strings(values):
    seen = set()
    distinct = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        distinct.append(text)
    return distinct


def _detect_failure_reason(action_lower, error_text, selector, validation):
    normalized = _normalize_text(error_text)
    selector_text = _normalize_text(selector)
    validation = validation if isinstance(validation, dict) else {}

    if action_lower == "navigate" and any(term in normalized for term in ["timeout", "timed out", "navigation timeout", "page.goto"]):
        return "navigation_timeout"

    if any(term in normalized for term in ["another element would receive the click", "click intercepted", "intercepted", "is obscured", "pointer-events"]):
        return "click_intercepted"

    if any(term in normalized for term in ["not visible", "outside of the viewport", "hidden", "element is not visible"]):
        return "element_not_visible"

    if any(term in normalized for term in ["strict mode violation", "selector not found", "no element matches", "no such element", "unable to find", "could not find", "missing element", "waiting for selector", "locator"]):
        return "selector_not_found"

    if action_lower in INPUT_ACTIONS and selector_text and any(term in selector_text for term in ["text=", "role=", "label=", "placeholder="]):
        return "selector_not_found"

    if action_lower in {"click", "hover", "wait", "select", "verify", "fill", "input", "enter", "enter_text", "input_text"}:
        if validation.get("expected_matched") is False and not normalized:
            return "selector_not_found"

    if "timeout" in normalized:
        return "navigation_timeout" if action_lower == "navigate" else "element_not_visible"

    if "not found" in normalized or "unable to find" in normalized:
        return "selector_not_found"

    if "not visible" in normalized or "hidden" in normalized:
        return "element_not_visible"

    return "unknown"


def _collect_recovery_candidates(step, selector, selector_hint, typed_value, dom, action_lower):
    texts = _distinct_strings([
        selector_hint,
        getattr(step, "target", None),
        selector,
        typed_value,
        getattr(step, "value", None),
    ])

    dom = dom or {}
    for button in dom.get("buttons", []) or []:
        texts.extend(_distinct_strings([button.get("text"), button.get("aria_label"), button.get("name")] ))
    for link in dom.get("links", []) or []:
        texts.extend(_distinct_strings([link.get("text")]))
    for input_el in dom.get("inputs", []) or []:
        texts.extend(_distinct_strings([input_el.get("placeholder"), input_el.get("name"), input_el.get("id")]))

    texts = _distinct_strings(texts)
    candidates = []
    seen = set()

    def add_candidate(method, value):
        value = str(value or "").strip()
        if not value:
            return
        key = (method, value)
        if key in seen:
            return
        seen.add(key)
        candidates.append({"method": method, "value": value})

    if selector:
        add_candidate("selector", selector)
    if selector_hint and selector_hint != selector:
        add_candidate("selector", selector_hint)

    for text in texts:
        add_candidate("text", text)
        if action_lower == "click":
            add_candidate("role_button", text)
            add_candidate("role_link", text)
        if action_lower in INPUT_ACTIONS:
            add_candidate("label", text)
            add_candidate("placeholder", text)
            add_candidate("role_textbox", text)

    return candidates


def _locator_for_candidate(page, candidate):
    method = candidate.get("method")
    value = candidate.get("value")
    if method == "selector":
        return page.locator(value).first
    if method == "text":
        return page.get_by_text(value, exact=False).first
    if method == "role_button":
        return page.get_by_role("button", name=value).first
    if method == "role_link":
        return page.get_by_role("link", name=value).first
    if method == "role_textbox":
        return page.get_by_role("textbox", name=value).first
    if method == "label":
        return page.get_by_label(value).first
    if method == "placeholder":
        return page.get_by_placeholder(value).first
    return page.locator(value).first


async def _execute_locator_action(page, locator, action_lower, typed_value, progress_callback=None, selector_label: str = ""):
    await _timed_call(progress_callback, f"recovery:scroll:{selector_label or action_lower}", locator.scroll_into_view_if_needed(), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})

    if action_lower == "click":
        try:
            await _timed_call(progress_callback, f"recovery:visible:{selector_label or action_lower}", locator.wait_for(state="visible", timeout=DEFAULT_RETRY_TIMEOUT_MS), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        except Exception:
            pass
        try:
            if await locator.is_enabled():
                await _timed_call(progress_callback, f"recovery:click:{selector_label or action_lower}", locator.click(), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
                return
        except Exception:
            pass
        await _timed_call(progress_callback, f"recovery:click-force:{selector_label or action_lower}", locator.click(force=True), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        return

    if action_lower in INPUT_ACTIONS:
        try:
            await _timed_call(progress_callback, f"recovery:visible:{selector_label or action_lower}", locator.wait_for(state="visible", timeout=DEFAULT_RETRY_TIMEOUT_MS), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        except Exception:
            pass
        try:
            if await locator.is_visible() and await locator.is_enabled():
                await _timed_call(progress_callback, f"recovery:fill:{selector_label or action_lower}", locator.fill(typed_value), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
                return
        except Exception:
            pass
        try:
            await _timed_call(progress_callback, f"recovery:click:{selector_label or action_lower}", locator.click(force=True), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
            await _timed_call(progress_callback, f"recovery:ctrl+a:{selector_label or action_lower}", page.keyboard.press("Control+A"), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
            await _timed_call(progress_callback, f"recovery:backspace:{selector_label or action_lower}", page.keyboard.press("Backspace"), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
            await _timed_call(progress_callback, f"recovery:type:{selector_label or action_lower}", page.keyboard.type(typed_value, delay=25), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
            return
        except Exception:
            pass
        await _timed_call(progress_callback, f"recovery:focus:{selector_label or action_lower}", locator.focus(), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        await _timed_call(progress_callback, f"recovery:type-fallback:{selector_label or action_lower}", page.keyboard.type(typed_value, delay=25), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        return

    if action_lower == "hover":
        await _timed_call(progress_callback, f"recovery:hover-visible:{selector_label or action_lower}", locator.wait_for(state="visible", timeout=DEFAULT_RETRY_TIMEOUT_MS), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        await _timed_call(progress_callback, f"recovery:hover:{selector_label or action_lower}", locator.hover(), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        return

    if action_lower == "wait":
        await _timed_call(progress_callback, f"recovery:wait-visible:{selector_label or action_lower}", locator.wait_for(state="visible", timeout=DEFAULT_RETRY_TIMEOUT_MS), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        return

    if action_lower == "select":
        await _timed_call(progress_callback, f"recovery:select-visible:{selector_label or action_lower}", locator.wait_for(state="visible", timeout=DEFAULT_RETRY_TIMEOUT_MS), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        await _timed_call(progress_callback, f"recovery:select:{selector_label or action_lower}", locator.select_option(value=typed_value or ""), timeout_ms=DEFAULT_RETRY_TIMEOUT_MS, meta={"selector": selector_label, "action": action_lower})
        return

    if action_lower == "verify":
        await locator.wait_for(state="visible", timeout=15000)
        return

    raise Exception(f"Unsupported recovery action: {action_lower}")


async def _collect_step_outcome(page, url, previous_url, test_case, target, selector, action_lower):
    url_changed = await check_url_change(page, previous_url)
    error_detected = await check_error_messages(page)
    snapshot = await get_page_snapshot(page)

    is_negative_test = any(
        keyword in (getattr(test_case, "expected", "") or "").lower()
        for keyword in ["error", "invalid", "failed", "required"]
    )

    if is_negative_test:
        status = "passed" if error_detected else "failed"
    else:
        status = "failed" if error_detected else "passed"

    expected_match = False
    success_flow = any(keyword in (((getattr(test_case, "title", "") or "") + " " + (getattr(test_case, "expected", "") or "")).lower()) for keyword in ["login", "sign in", "authenticate", "success", "dashboard", "welcome", "home", "profile", "account"])
    if success_flow:
        expected_match = await detect_success_state(page, previous_url)
    elif getattr(test_case, "expected", None):
        expected_match = await check_expected_text(page, test_case.expected)

    if not is_same_domain(url, page.url):
        raise Exception("Navigation outside allowed domain detected")

    return {
        "status": status,
        "url_changed": url_changed,
        "error_detected": error_detected,
        "snapshot": snapshot,
        "expected_match": expected_match,
        "is_negative_test": is_negative_test,
    }


async def _attempt_step_recovery(page, *, action_lower, step, selector, selector_hint, typed_value, dom, url, previous_url, test_case, progress_callback, error_text="", validation=None):
    reason = _detect_failure_reason(action_lower, error_text, selector, validation or {})
    if reason == "unknown":
        if action_lower in {"click", "fill", "input", "type", "enter", "enter_text", "input_text", "hover", "wait", "select", "verify", "navigate"}:
            reason = "generic_retry"
        else:
            return {
                "recovery_attempted": False,
                "recovery_success": False,
                "recovery_type": "",
                "recovery_actions": [],
                "validation": None,
                "error": error_text,
            }

    recovery_actions = []
    candidates = _collect_recovery_candidates(step, selector, selector_hint, typed_value, dom, action_lower)

    async def _try_candidate(candidate, detail):
        record = {
            "type": reason,
            "method": candidate.get("method", ""),
            "selector": candidate.get("value", ""),
            "detail": detail,
            "success": False,
        }
        await _emit_progress(progress_callback, {
            "type": "recovery_attempt",
            "message": detail,
            "step": step.model_dump(),
            "recovery_type": reason,
            "recovery_method": candidate.get("method", ""),
        })
        try:
            locator = _locator_for_candidate(page, candidate)
            await _execute_locator_action(page, locator, action_lower, typed_value, progress_callback=progress_callback, selector_label=str(candidate.get("value") or ""))
            record["success"] = True
            return record
        except Exception as exc:
            record["error"] = str(exc)
            return record

    if reason == "navigation_timeout" and getattr(step, "value", None):
        record = {
            "type": reason,
            "method": "goto",
            "selector": getattr(step, "value", ""),
            "detail": f"Retrying navigation with extended timeout: {step.value}",
            "success": False,
        }
        await _emit_progress(progress_callback, {
            "type": "recovery_attempt",
            "message": record["detail"],
            "step": step.model_dump(),
            "recovery_type": reason,
            "recovery_method": "goto",
        })
        try:
            await page.goto(step.value, wait_until="domcontentloaded", timeout=90000)
            record["success"] = True
            recovery_actions.append(record)
        except Exception as exc:
            record["error"] = str(exc)
            recovery_actions.append(record)
    else:
        for attempt_index, candidate in enumerate(candidates, start=1):
            if attempt_index > MAX_SELECTOR_RETRY_ATTEMPTS:
                break
            if reason == "click_intercepted" and candidate.get("method") not in {"selector", "text", "role_button", "role_link"}:
                continue
            if reason == "element_not_visible" and candidate.get("method") not in {"selector", "text", "role_button", "role_link", "role_textbox", "label", "placeholder"}:
                continue
            record = await _try_candidate(
                candidate,
                f"Retrying {action_lower} via {candidate.get('method')} locator: {candidate.get('value')}"
            )
            recovery_actions.append(record)
            if record.get("success"):
                break

        if reason == "click_intercepted" and not any(item.get("success") for item in recovery_actions):
            try:
                original = _locator_for_candidate(page, {"method": "selector", "value": selector})
                await _emit_progress(progress_callback, {
                    "type": "recovery_attempt",
                    "message": f"Retrying click with JavaScript fallback: {selector or selector_hint or step.target}",
                    "step": step.model_dump(),
                    "recovery_type": reason,
                    "recovery_method": "javascript_click",
                })
                await original.evaluate("element => element.click()")
                recovery_actions.append({
                    "type": reason,
                    "method": "javascript_click",
                    "selector": selector,
                    "detail": "Triggered a JavaScript click fallback.",
                    "success": True,
                })
            except Exception as exc:
                recovery_actions.append({
                    "type": reason,
                    "method": "javascript_click",
                    "selector": selector,
                    "detail": "Triggered a JavaScript click fallback.",
                    "success": False,
                    "error": str(exc),
                })

    action_recovered = any(item.get("success") for item in recovery_actions)
    validation_result = None
    if action_recovered:
        validation_result = await _collect_step_outcome(page, url, previous_url, test_case, getattr(step, "target", ""), selector, action_lower)

    recovery_success = bool(validation_result and validation_result.get("status") == "passed")

    return {
        "recovery_attempted": bool(recovery_actions),
        "recovery_success": recovery_success,
        "recovery_type": reason if recovery_actions else "",
        "recovery_actions": recovery_actions,
        "validation": validation_result,
        "error": error_text,
    }


INPUT_ACTIONS = {"type", "enter", "fill", "input", "enter_text", "input_text"}


def _normalize_text(value):
    return " ".join((value or "").strip().lower().replace("_", " ").split())


def _input_score(target_lower: str, input_el: dict) -> int:
    name = _normalize_text(input_el.get("name") or "")
    placeholder = _normalize_text(input_el.get("placeholder") or "")
    input_id = _normalize_text(input_el.get("id") or "")
    aria_label = _normalize_text(input_el.get("aria_label") or "")
    label = _normalize_text(input_el.get("label") or "")
    input_type = _normalize_text(input_el.get("type") or "")
    role = _normalize_text(input_el.get("role") or "")

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


def _looks_like_field_hint(text):
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in ["username", "user name", "email", "password", "login button", "sign in", "field", "input", "textbox", "label"])


def _looks_like_selector(text):
    normalized = (text or "").strip()
    return any(token in normalized for token in ["#", ".", "[", "]", "=", "text="])


def _hint_to_label(text):
    normalized = _normalize_text(text)
    if any(keyword in normalized for keyword in ["username", "user name", "email"]):
        return "username field"
    if "password" in normalized:
        return "password field"
    if any(keyword in normalized for keyword in ["login button", "sign in", "log in", "submit"]):
        return "login button"
    return text


def _looks_like_success_subject(text):
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in [
        "success",
        "dashboard",
        "welcome",
        "home",
        "overview",
        "account",
        "profile",
        "authenticated",
        "logged in",
        # Inventory / product related keywords common in ecommerce flows
        "inventory",
        "product",
        "products",
        "catalog",
        "checkout complete",
    ])


def _resolve_saucedemo_verification_target(target, selector):
    subject = (target or selector or "").strip() if isinstance(target or selector or "", str) else ""
    if not subject:
        return None
    if _looks_like_selector(subject):
        return subject

    normalized = _normalize_text(subject)
    if normalized in {"selected item", "selected items", "cart item", "cart items"}:
        return ".cart_item"
    if normalized in {"order confirmation", "confirmation", "checkout confirmation", "thank you for your order"}:
        return ".complete-header"

    if not _looks_like_saucedemo_semantic_target(subject):
        return None

    resolved = resolve_selector(subject, {})
    if isinstance(resolved, dict):
        candidate = (resolved.get("selector") or "").strip()
        if candidate and candidate != subject:
            return candidate
    return None


def _looks_like_saucedemo_semantic_target(text):
    normalized = _normalize_text(text)
    return normalized in {
        "username input",
        "password input",
        "login button",
        "inventory page",
        "cart page",
        "cart badge",
        "cart link",
        "add to cart",
        "checkout",
        "first name",
        "last name",
        "postal code",
        "continue",
        "finish",
        "checkout complete",
    }


def _scenario_context_tokens(test_case) -> set[str]:
    tokens = set()
    if not test_case:
        return tokens
    values = [
        getattr(test_case, "feature_key", None),
        getattr(test_case, "objective_name", None),
        getattr(test_case, "scenario_name", None),
        getattr(test_case, "title", None),
        getattr(test_case, "expected", None),
    ]
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            tokens.update(part for part in normalized.split() if part)
    return tokens


def _contextual_input_score(target_lower: str, input_el: dict, context_tokens: set[str]) -> int:
    score = _input_score(target_lower, input_el)
    haystack = " ".join(
        _normalize_text(input_el.get(key) or "")
        for key in ("name", "placeholder", "id", "aria_label", "label", "type")
    )
    if any(token in haystack for token in context_tokens):
        score += 25
    if context_tokens and any(token in {"login", "signin", "sign", "auth", "authentication", "password", "username", "email"} for token in context_tokens):
        if any(keyword in haystack for keyword in ["login", "sign", "auth", "email", "user", "password", "username"]):
            score += 20
    return score


def _selector_matches_context(selector: str | None, test_case) -> bool:
    if not selector:
        return False
    normalized = _normalize_text(selector)
    context_tokens = _scenario_context_tokens(test_case)
    if not context_tokens:
        return True
    if any(token in normalized for token in context_tokens):
        return True
    if any(token in normalized for token in ["login", "sign in", "authentication", "auth", "username", "password", "email"]):
        return any(token in context_tokens for token in ["login", "sign", "auth", "authentication", "username", "password", "email"])
    if any(token in normalized for token in ["cart", "checkout", "inventory", "item", "product", "order", "payment"]):
        return any(token in context_tokens for token in ["cart", "checkout", "inventory", "item", "product", "order", "payment"])
    return False


def _resolve_step_final_status(*, action_lower: str, recovery_info: dict | None, validation_payload: dict | None, test_case, execution_failed: bool = False) -> str:
    if recovery_info and recovery_info.get("recovery_success"):
        return "passed"
    if execution_failed:
        return "failed"
    if action_lower == "verify" and validation_payload is not None:
        if validation_payload.get("expected_matched") is False or validation_payload.get("error_detected"):
            return "failed"
    if validation_payload is not None and validation_payload.get("error_detected"):
        is_negative_test = any(
            keyword in (getattr(test_case, "expected", "") or "").lower()
            for keyword in ["error", "invalid", "failed", "required"]
        )
        return "passed" if is_negative_test else "failed"
    return "passed"


def _build_step_execution_context(page, test_case, previous_successful_actions: list[str], authenticated: bool, current_title: str = "", current_url: str = "") -> dict:
    try:
        current_url = current_url or (page.url if hasattr(page, "url") else "")
    except Exception:
        current_url = current_url or ""
    return {
        "current_objective": getattr(test_case, "objective_name", None) or getattr(test_case, "title", None),
        "current_scenario": getattr(test_case, "scenario_name", None) or getattr(test_case, "title", None),
        "current_page": current_url,
        "current_page_title": current_title,
        "current_authenticated_state": authenticated,
        "previous_successful_actions": list(previous_successful_actions),
    }


def _resolve_step_selector(step, dom, test_case=None, current_url: str = ""):
    # Build candidate hints
    candidates = []
    context_tokens = _scenario_context_tokens(test_case)
    selector_context = {
        "page_url": current_url,
        "url": current_url,
        "current_url": current_url,
        "feature_key": getattr(test_case, "feature_key", None),
        "objective_name": getattr(test_case, "objective_name", None),
        "scenario_name": getattr(test_case, "scenario_name", None),
        "action": _normalize_text(step.action),
    }
    if step.selector:
        candidates.append(step.selector)
    if step.target and not (_normalize_text(step.action) in INPUT_ACTIONS and not _looks_like_field_hint(step.target)):
        candidates.append(step.target)

    # Try candidates with resolver which now returns diagnostics dict
    for candidate in candidates:
        resolved_info = resolve_selector(candidate, dom or {}, context=selector_context)
        selector = resolved_info.get("selector") if isinstance(resolved_info, dict) else resolved_info
        # Emit selector diagnostics
        try:
            # progress callback not available here; return diagnostics via tuple
            pass
        except Exception:
            pass
        if selector:
            return selector, candidate

    # For input actions, try hint-based and contextual scoring
    if _normalize_text(step.action) in INPUT_ACTIONS:
        hint = _hint_to_label(step.selector or step.target or "")
        resolved_info = resolve_selector(hint, dom or {}, context=selector_context)
        selector = resolved_info.get("selector") if isinstance(resolved_info, dict) else resolved_info
        if selector:
            return selector, hint

        inputs = (dom or {}).get("inputs", [])
        if any(keyword in _normalize_text(step.selector or step.target or step.value or "") for keyword in ["password"]):
            if len(inputs) > 1:
                second = inputs[1]
                password_hint = second.get("placeholder") or second.get("name") or second.get("id") or "password field"
                password_selector_info = resolve_selector(password_hint, dom or {}, context=selector_context)
                password_selector = password_selector_info.get("selector") if isinstance(password_selector_info, dict) else password_selector_info
                if password_selector:
                    return password_selector, "password field"
                return f'input[type="password"]', "password field"

        if any(keyword in _normalize_text(step.selector or step.target or step.value or "") for keyword in ["username", "user name", "email"]):
            if inputs:
                ranked_inputs = sorted(
                    inputs,
                    key=lambda input_el: _contextual_input_score(_normalize_text(step.selector or step.target or step.value or ""), input_el, context_tokens),
                    reverse=True,
                )
                best_input = ranked_inputs[0]
                best_score = _contextual_input_score(_normalize_text(step.selector or step.target or step.value or ""), best_input, context_tokens)
                if best_score > 0:
                    best_hint = best_input.get("placeholder") or best_input.get("name") or best_input.get("id") or "username field"
                    best_info = resolve_selector(best_hint, dom or {}, context=selector_context)
                    best_sel = best_info.get("selector") if isinstance(best_info, dict) else best_info
                    if best_sel:
                        return best_sel, "username field"

        ranked_inputs = sorted(
            inputs,
            key=lambda input_el: _contextual_input_score(_normalize_text(step.selector or step.target or step.value or ""), input_el, context_tokens),
            reverse=True,
        )
        if ranked_inputs:
            best_input = ranked_inputs[0]
            best_score = _contextual_input_score(_normalize_text(step.selector or step.target or step.value or ""), best_input, context_tokens)
            if best_score > 0:
                hint = best_input.get("placeholder") or best_input.get("name") or best_input.get("id") or step.target or "field"
                resolved_info = resolve_selector(hint, dom or {}, context=selector_context)
                resolved = resolved_info.get("selector") if isinstance(resolved_info, dict) else resolved_info
                if resolved:
                    return resolved, best_input.get("placeholder") or best_input.get("name") or best_input.get("id") or step.target

    # If a concrete selector was provided directly on the step, accept it only if it looks like a selector
    if step.selector and _looks_like_selector(step.selector):
        return step.selector, step.selector

    # Don't return semantic text selectors as final; fail-fast into recovery by returning None
    if _normalize_text(step.action) in INPUT_ACTIONS:
        return None, step.selector or step.target

    if step.target and _normalize_text(step.action) not in INPUT_ACTIONS:
        # For non-inputs we may use text locator, but mark as text-based
        return f'text="{step.target}"', step.target

    return None, step.selector or step.target


async def _emit_progress(progress_callback, payload):
    if not progress_callback:
        return
    result = progress_callback(payload)
    if inspect.isawaitable(result):
        await result



def _empty_recovery_info(error_text="", *, attempted=False, recovery_error=None):
    return {
        "recovery_attempted": attempted,
        "recovery_success": False,
        "recovery_type": "",
        "recovery_actions": [],
        "validation": None,
        "error": error_text,
        "recovery_error": recovery_error,
    }


async def _safe_attempt_step_recovery(page, **kwargs):
    progress_callback = kwargs.get("progress_callback")
    step = kwargs.get("step")
    try:
        return await _attempt_step_recovery(page, **kwargs)
    except Exception as exc:
        await _emit_progress(progress_callback, {
            "type": "recovery_error",
            "message": "Recovery attempt failed; recording step failure and continuing",
            "step": step.model_dump() if hasattr(step, "model_dump") else step,
            "error": str(exc),
        })
        return _empty_recovery_info(
            kwargs.get("error_text") or str(exc),
            attempted=True,
            recovery_error=str(exc),
        )


async def _capture_step_screenshot(page, step, progress_callback, label="observation"):
    try:
        screenshot = await asyncio.wait_for(page.screenshot(full_page=False), timeout=DEFAULT_SCREENSHOT_TIMEOUT_MS / 1000)
        await _emit_progress(progress_callback, {
            "type": "screenshot",
            "label": label,
            "step": step.model_dump() if hasattr(step, "model_dump") else step,
            "screenshot_b64": base64.b64encode(screenshot).decode("ascii"),
        })
    except Exception:
        pass


def _build_execution_metrics(total_tasks, results):
    success_statuses = {"pass", "passed", "completed"}
    failure_statuses = {"fail", "failed", "error"}
    completed_tasks = sum(1 for item in results if isinstance(item, dict) and item.get("status") in success_statuses)
    failed_tasks = sum(1 for item in results if isinstance(item, dict) and item.get("status") in failure_statuses)
    skipped_tasks = max(0, total_tasks - len(results))
    recovery_attempts = sum(len(item.get("recovery_actions", [])) for item in results if isinstance(item, dict))
    successful_recoveries = sum(1 for item in results if isinstance(item, dict) and item.get("recovery_success"))
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "successful_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "skipped_tasks": skipped_tasks,
        "recovery_attempts": recovery_attempts,
        "successful_recoveries": successful_recoveries,
    }


async def run_test_steps(url: str, test_case, dom: dict = None,credentials: dict = None, progress_callback=None, shared_state: dict | None = None, session_manager: BrowserSessionManager | None = None):
    # Ensure subprocess-compatible loop policy for Windows worker/background contexts.
    ensure_windows_event_loop_policy()
    shared_state = shared_state or {}
    cleanup_completed = False
    try:
        storage_state = shared_state.get("storage_state")
        if isinstance(storage_state, str) and storage_state and not os.path.exists(storage_state):
            storage_state = None

        # Prefer a shared BrowserSessionManager when provided to avoid launching a browser per scenario.
        using_shared_manager = session_manager is not None
        session = None
        p = None
        browser = None

        async def _cleanup_runtime_resources(reason: str) -> None:
            nonlocal cleanup_completed
            if cleanup_completed:
                return
            cleanup_completed = True

            if using_shared_manager and session is not None:
                try:
                    await asyncio.wait_for(asyncio.shield(session.close()), timeout=20)
                    logger.info("Closed shared browser session after %s", reason)
                except asyncio.CancelledError:
                    logger.warning("Shared browser session cleanup was cancelled during %s", reason)
                except Exception as cleanup_exc:
                    logger.warning("Shared browser session cleanup failed during %s: %s", reason, cleanup_exc)
                return

            if browser is not None:
                try:
                    await asyncio.wait_for(asyncio.shield(browser.close()), timeout=15)
                    logger.info("Closed browser after %s", reason)
                except asyncio.CancelledError:
                    logger.warning("Browser cleanup was cancelled during %s", reason)
                except Exception as cleanup_exc:
                    logger.warning("Browser cleanup failed during %s: %s", reason, cleanup_exc)

            if p is not None:
                try:
                    await asyncio.wait_for(asyncio.shield(p.stop()), timeout=15)
                    logger.info("Stopped Playwright after %s", reason)
                except asyncio.CancelledError:
                    logger.warning("Playwright cleanup was cancelled during %s", reason)
                except Exception as cleanup_exc:
                    logger.warning("Playwright cleanup failed during %s: %s", reason, cleanup_exc)

        if using_shared_manager:
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Using shared BrowserSessionManager"})
            session = await session_manager.new_session(storage_state=storage_state)
            context = session.context
            page = session.page
            console_errors = session.signals.console_errors
            network_failures = session.signals.network_failures
            previous_successful_actions = list(shared_state.get("previous_successful_actions") or [])
            authenticated = bool(shared_state.get("authenticated"))
            # signal handlers are attached by the session manager for shared sessions
        else:
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Launching Playwright"})
            p = await async_playwright().start()
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Playwright started"})
            browser = await p.chromium.launch(headless=True)
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Browser launched"})
            context = await browser.new_context(storage_state=storage_state, ignore_https_errors=True)
            page = await context.new_page()
            console_errors = []
            network_failures = []
            previous_successful_actions = list(shared_state.get("previous_successful_actions") or [])
            authenticated = bool(shared_state.get("authenticated"))

            def _message_text(message):
                value = getattr(message, "text", "")
                return value() if callable(value) else str(value)

            def _message_type(message):
                value = getattr(message, "type", "")
                return value() if callable(value) else str(value)

            def _message_location(message):
                value = getattr(message, "location", {})
                value = value() if callable(value) else value
                if isinstance(value, dict):
                    url = str(value.get("url") or "")
                    line_number = value.get("lineNumber")
                    column_number = value.get("columnNumber")
                    location_bits = []
                    if url:
                        location_bits.append(url)
                    if line_number is not None:
                        location_bits.append(str(int(line_number) + 1))
                    if column_number is not None:
                        location_bits.append(str(int(column_number) + 1))
                    return ":".join(location_bits)
                return ""

            def _request_url(request):
                value = getattr(request, "url", "")
                return value() if callable(value) else str(value)

            def _request_method(request):
                value = getattr(request, "method", "")
                return value() if callable(value) else str(value)

            def _request_failure_text(request):
                value = getattr(request, "failure", None)
                value = value() if callable(value) else value
                if isinstance(value, dict):
                    return str(value.get("errorText") or "")
                return str(value or "")

            def _capture_console(message):
                try:
                    if _message_type(message) != "error":
                        return
                    entry = _message_text(message)
                    location = _message_location(message)
                    if location:
                        entry = f"{entry} ({location})"
                    console_errors.append(entry)
                except Exception:
                    pass

            def _capture_request_failed(request):
                try:
                    failure_text = _request_failure_text(request)
                    request_url = _request_url(request)
                    request_method = _request_method(request)
                    parts = [piece for piece in [request_method, request_url, failure_text] if piece]
                    if parts:
                        network_failures.append(" | ".join(parts))
                except Exception:
                    pass

            page.on("console", _capture_console)
            page.on("requestfailed", _capture_request_failed)

        # Open the target URL (shared and non-shared sessions both follow this path)
        await _emit_progress(progress_callback, {"type": "run_status", "message": f"Opening {url}"})
        try:
            await _timed_call(progress_callback, f"goto:{url}:commit", page.goto(url, wait_until="commit", timeout=DEFAULT_NAVIGATION_TIMEOUT_MS), timeout_ms=DEFAULT_NAVIGATION_TIMEOUT_MS, meta={"url": url})
            # Wait for body to be visible — this is the real readiness signal
            try:
                await page.locator("body").first.wait_for(state="visible", timeout=15000)
            except Exception:
                pass  # Body might not be visible yet on very slow sites; continue anyway
        except Exception:
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Retrying page load"})
            await _timed_call(progress_callback, f"goto:{url}:domcontentloaded", page.goto(url, wait_until="domcontentloaded", timeout=60000), timeout_ms=60000, meta={"url": url})
        if shared_state.get("session_storage"):
            try:
                await page.evaluate(
                    """
                    (items) => {
                      for (const [key, value] of Object.entries(items || {})) {
                        sessionStorage.setItem(key, String(value));
                      }
                    }
                    """,
                    shared_state.get("session_storage") or {},
                )
            except Exception:
                pass
        await _emit_progress(progress_callback, {
            "type": "run_status",
            "message": f"Opened {url}",
        })

        await _ensure_saucedemo_authenticated_landing(
            page,
            url,
            test_case,
            authenticated,
            progress_callback=progress_callback,
        )

        steps_to_run = list(test_case.steps or [])
        results = []
        previous_url = page.url
        scenario_label_for_log = getattr(test_case, "scenario_id", None) or getattr(test_case, "scenario_name", None) or "unknown"
        total_steps_for_log = len(steps_to_run)
        logger.info(
            "Step loop start: scenario=%s  total_steps=%d",
            scenario_label_for_log,
            total_steps_for_log,
        )

        for step_index, step in enumerate(steps_to_run, start=1):
            step_started = perf_counter()
            step_timeout_seconds = 30
            logger.info(
                "Executing step %d/%d: action=%s target=%s scenario=%s",
                step_index,
                total_steps_for_log,
                getattr(step, "action", "?"),
                getattr(step, "target", "?"),
                scenario_label_for_log,
            )

            def _check_step_budget(checkpoint: str):
                elapsed = perf_counter() - step_started
                if elapsed > step_timeout_seconds:
                    raise TimeoutError(f"Step timeout after {elapsed:.1f}s at {checkpoint}")

            action = step.action
            target = step.target
            value = step.value
            action_lower = (action or "").lower()
            await _emit_progress(progress_callback, {
                "type": "step_started",
                "message": f"Starting step {step_index}/{total_steps_for_log}: {action or 'action'}"
                + (f" on {target}" if target else ""),
                "step": step.model_dump(),
                "step_index": step_index,
                "total_steps": total_steps_for_log,
                "scenario_id": getattr(test_case, "scenario_id", None),
                "scenario_name": getattr(test_case, "scenario_name", None),
            })

            # DYNAMIC CREDENTIAL INJECTION
            if (
                value
                and isinstance(value, str)
                and value.startswith("{")
                and value.endswith("}")
            ):
                key = value.replace("{", "").replace("}", "").strip()
                if credentials and key in credentials:
                    value = credentials[key]

            selector_resolution_started = perf_counter()
            await _emit_progress(progress_callback, {
                "type": "timing",
                "phase": "start",
                "label": "selector_resolution",
                "step": step.model_dump(),
            })
            # Refresh live DOM for accurate resolution (ensures resolver sees current page state)
            try:
                live_inputs = await page.eval_on_selector_all('input', "nodes => nodes.map(n => ({name: n.name, placeholder: n.placeholder, id: n.id, aria_label: n.getAttribute('aria-label'), label: (n.labels && n.labels.length>0)? n.labels[0].innerText: null, type: n.type}))")
                live_buttons = await page.eval_on_selector_all('button, input[type=submit], a', "nodes => nodes.map(n => ({text: n.innerText || n.value || n.getAttribute('aria-label') || '', aria_label: n.getAttribute('aria-label'), id: n.id, name: n.name, class: n.className, type: n.type}))")
                live_links = await page.eval_on_selector_all('a', "nodes => nodes.map(n => ({text: n.innerText || '', href: n.href}))")
                live_dom = {"inputs": live_inputs or [], "buttons": live_buttons or [], "links": live_links or []}
            except Exception:
                live_dom = dom or {}

            selector, selector_hint = _resolve_step_selector(step, live_dom, test_case, current_url=page.url)
            await _emit_progress(progress_callback, {
                "type": "timing",
                "phase": "end",
                "label": "selector_resolution",
                "elapsed_ms": round((perf_counter() - selector_resolution_started) * 1000, 1),
                "step": step.model_dump(),
                "selector": selector,
                "selector_hint": selector_hint,
            })
            # Emit selector diagnostics with resolver candidate trace (best-effort)
            try:
                diag_info = None
                if selector_hint:
                    diag_info = resolve_selector(selector_hint, dom or {}, context={"page_url": page.url, "url": page.url, "current_url": page.url, "feature_key": getattr(test_case, "feature_key", None), "objective_name": getattr(test_case, "objective_name", None), "scenario_name": getattr(test_case, "scenario_name", None), "action": action_lower})
                elif target:
                    diag_info = resolve_selector(target, dom or {}, context={"page_url": page.url, "url": page.url, "current_url": page.url, "feature_key": getattr(test_case, "feature_key", None), "objective_name": getattr(test_case, "objective_name", None), "scenario_name": getattr(test_case, "scenario_name", None), "action": action_lower})
                if isinstance(diag_info, dict):
                    await _emit_progress(progress_callback, {
                        "type": "selector_diagnostics",
                        "original_target": selector_hint or target,
                        "resolved_selector": selector,
                        "source": diag_info.get("source"),
                        "candidates": diag_info.get("candidates"),
                        "unresolved": diag_info.get("unresolved"),
                        "cache_hit": diag_info.get("cache_hit"),
                        "confidence": diag_info.get("confidence"),
                        "step": step.model_dump(),
                    })
            except Exception:
                pass
            if not selector and target and action_lower not in INPUT_ACTIONS and not _looks_like_saucedemo_semantic_target(target):
                selector = f'text="{target}"'
            _check_step_budget("after_selector_resolution")

            display_name = selector_hint or target or selector or "unknown target"
            try:
                current_title = await _timed_call(progress_callback, f"title:{display_name}", page.title(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"step": step.model_dump(), "display_name": display_name})
            except Exception:
                current_title = ""
            step_execution_context = _build_step_execution_context(page, test_case, previous_successful_actions, authenticated, current_title=current_title)
            selector_fallback_used = bool(selector_hint and selector_hint != getattr(step, "selector", None)) or (action_lower in INPUT_ACTIONS and not getattr(step, "selector", None) and bool(selector))

            try:
                typed_value = value or ""
                if action_lower in INPUT_ACTIONS and not typed_value and target and not _looks_like_field_hint(target):
                    typed_value = target

                # Fail-fast for unresolved input selectors to avoid long Playwright timeouts
                if action_lower in INPUT_ACTIONS and not selector:
                    raise Exception("Selector unresolved for input action; failing fast to recovery")

                await _emit_progress(progress_callback, {
                    "type": "action_execution",
                    "message": f"Executing {action} on {display_name}",
                    "step": step.model_dump(),
                    "execution_context": step_execution_context,
                })

                if action_lower == "click":
                    await _emit_progress(progress_callback, {"type": "action_execution", "message": f"Clicking {display_name}", "step": step.model_dump()})
                    if isinstance(selector, str) and "add-to-cart" in selector:
                        try:
                            add_count = await page.locator(selector).count()
                            if add_count == 0:
                                # If add-to-cart buttons are gone but remove/cart indicators exist,
                                # treat this step as already satisfied for idempotent reruns.
                                remove_count = await page.locator('button[data-test*="remove"]').count()
                                badge_count = await page.locator(".shopping_cart_badge").count()
                                if remove_count > 0 or badge_count > 0:
                                    await _emit_progress(progress_callback, {
                                        "type": "run_status",
                                        "message": "Add-to-cart already satisfied; item appears to already be in cart",
                                    })
                                else:
                                    await safe_click(page, selector, progress_callback=progress_callback)
                            else:
                                await safe_click(page, selector, progress_callback=progress_callback)
                        except Exception:
                            await safe_click(page, selector, progress_callback=progress_callback)
                    else:
                        await safe_click(page, selector, progress_callback=progress_callback)
                elif action_lower in INPUT_ACTIONS:
                    await _emit_progress(progress_callback, {"type": "action_execution", "message": f"Found {display_name}", "step": step.model_dump()})
                    await _emit_progress(progress_callback, {"type": "action_execution", "message": f"Typing value into {display_name}", "step": step.model_dump()})
                    await safe_fill(page, selector, typed_value, progress_callback=progress_callback)
                elif action_lower == "press":
                    await _timed_call(progress_callback, f"keypress:{value}", page.keyboard.press(value), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"key": value})
                elif action_lower == "wait":
                    await safe_wait(page, selector, progress_callback=progress_callback)
                elif action_lower == "hover":
                    await safe_hover(page, selector, progress_callback=progress_callback)
                elif action_lower == "select":
                    await safe_select(page, selector, value or "", progress_callback=progress_callback)
                elif action_lower == "navigate":
                    if value and isinstance(value, str):
                        await _emit_progress(progress_callback, {"type": "run_status", "message": f"Navigating to URL {value}"})
                        await _timed_call(progress_callback, f"goto:{value}:domcontentloaded", page.goto(value, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT_MS), timeout_ms=DEFAULT_NAVIGATION_TIMEOUT_MS, meta={"url": value})
                elif action_lower == "verify":
                    verify_subject = (target or selector or "").strip() if isinstance(target or selector or "", str) else ""
                    verify_value = (value or "").strip().lower() if isinstance(value or "", str) else ""
                    if verify_subject:
                        resolved_verify_selector = _resolve_saucedemo_verification_target(target, selector)
                        _from_semantic = bool(resolved_verify_selector)
                        _from_resolver = False
                        if not resolved_verify_selector and selector and _looks_like_selector(selector):
                            resolved_verify_selector = selector
                            _from_resolver = True
                        if resolved_verify_selector:
                            _verify_source = "semantic_target" if _from_semantic else "resolver_fallback" if _from_resolver else "generic_selector"
                            logger.info(
                                "Verify dispatch: subject=%r resolved=%r source=%s context_check=%s",
                                verify_subject, resolved_verify_selector, _verify_source,
                                "skipped" if (_from_semantic or _from_resolver) else "applied",
                            )
                        subject_lower = verify_subject.lower()

                        # --- Page-level verification (e.g. "page title" with value "visible") ---
                        # Confirms the page loaded by checking for a non-empty title and visible body.
                        _is_page_level_verify = subject_lower in {"page title", "page loaded", "page state", "page visible"}
                        if _is_page_level_verify:
                            current_title = await _timed_call(
                                progress_callback,
                                f"verify:page_title:{verify_subject}",
                                page.title(),
                                timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS,
                                meta={"step": step.model_dump(), "verify_subject": verify_subject},
                            )
                            body_locator = page.locator("body").first
                            await body_locator.wait_for(state="visible", timeout=5000)
                            if not current_title or not current_title.strip():
                                raise Exception("Page title verification failed: title is empty")
                            await _emit_progress(progress_callback, {
                                "type": "run_status",
                                "message": f"Page title verified: {current_title}",
                            })
                        elif verify_value in {"visible", "present", "exists", "exist"}:
                            if resolved_verify_selector:
                                if not _from_semantic and not _from_resolver and not _selector_matches_context(resolved_verify_selector, test_case):
                                    raise Exception(f"Cross-feature selector reuse rejected for verification: {verify_subject}")
                                locator = page.locator(resolved_verify_selector).first
                                await locator.wait_for(state="visible", timeout=5000)
                            elif _looks_like_success_subject(verify_subject):
                                if not await detect_success_state(page, previous_url):
                                    raise Exception(f"Success-state verification failed for expected state: {verify_subject}")
                            elif _looks_like_selector(verify_subject):
                                if not _selector_matches_context(verify_subject, test_case):
                                    raise Exception(f"Cross-feature selector reuse rejected for verification: {verify_subject}")
                                locator = page.locator(verify_subject).first
                                await locator.wait_for(state="visible", timeout=5000)
                            else:
                                if not await check_expected_text(page, verify_subject):
                                    raise Exception(f"Verification failed for expected text: {verify_subject}")
                        else:
                            if resolved_verify_selector:
                                if not _from_semantic and not _from_resolver and not _selector_matches_context(resolved_verify_selector, test_case):
                                    raise Exception(f"Cross-feature selector reuse rejected for verification: {verify_subject}")
                                locator = page.locator(resolved_verify_selector).first
                                await locator.wait_for(state="visible", timeout=5000)
                            elif _looks_like_success_subject(verify_subject):
                                if not await detect_success_state(page, previous_url):
                                    raise Exception(f"Success-state verification failed for expected state: {verify_subject}")
                            elif "title" in (target or "").lower():
                                current_title = await _timed_call(progress_callback, f"verify:title:{verify_subject}", page.title(), timeout_ms=DEFAULT_SELECTOR_TIMEOUT_MS, meta={"step": step.model_dump(), "verify_subject": verify_subject})
                                if not current_title or not current_title.strip():
                                    raise Exception(f"Title verification failed: page has no title")
                            elif _looks_like_selector(verify_subject):
                                if not _selector_matches_context(verify_subject, test_case):
                                    raise Exception(f"Cross-feature selector reuse rejected for verification: {verify_subject}")
                                locator = page.locator(verify_subject).first
                                await locator.wait_for(state="visible", timeout=5000)
                            else:
                                matched = await check_expected_text(page, verify_subject)
                                if not matched:
                                    raise Exception(f"Verification failed for expected text: {verify_subject}")
                elif action == "screenshot":
                    # explicit screenshot action; binary is emitted below in common capture block
                    pass

                _check_step_budget("after_action")

                # VALIDATION CHECKS
                _check_step_budget("before_validation")
                validation_started = perf_counter()
                await _emit_progress(progress_callback, {"type": "timing", "phase": "start", "label": "validation", "step": step.model_dump()})
                url_changed = await check_url_change(page, previous_url)
                error_detected = await check_error_messages(page)
                snapshot = await get_page_snapshot(page)
                await _emit_progress(progress_callback, {
                    "type": "timing",
                    "phase": "end",
                    "label": "validation",
                    "elapsed_ms": round((perf_counter() - validation_started) * 1000, 1),
                    "step": step.model_dump(),
                    "snapshot": snapshot,
                })
                _check_step_budget("after_validation")

                # capture a per-step screenshot (best-effort)
                screenshot_started = perf_counter()
                await _emit_progress(progress_callback, {"type": "timing", "phase": "start", "label": "screenshot", "step": step.model_dump()})
                await _capture_step_screenshot(page, step, progress_callback)
                await _emit_progress(progress_callback, {"type": "timing", "phase": "end", "label": "screenshot", "elapsed_ms": round((perf_counter() - screenshot_started) * 1000, 1), "step": step.model_dump()})
                _check_step_budget("after_screenshot")

                previous_url = page.url

                if not is_same_domain(url, page.url):
                    raise Exception("Navigation outside allowed domain detected")

                is_negative_test = any(
                    keyword in (test_case.expected or "").lower()
                    for keyword in ["error", "invalid", "failed", "required"]
                )
                if is_negative_test:
                    status = "passed" if error_detected else "failed"
                else:
                    status = "failed" if error_detected else "passed"

                expected_match = action_lower == "verify"
                success_flow = any(keyword in ((test_case.title or "") + " " + (test_case.expected or "")).lower() for keyword in ["login", "sign in", "authenticate", "success", "dashboard", "welcome", "home", "profile", "account"])
                if action_lower == "verify":
                    expected_match = True
                elif success_flow:
                    expected_match = await detect_success_state(page, previous_url)
                    if expected_match:
                        await _emit_progress(progress_callback, {"type": "run_status", "message": "Success state detected"})
                elif hasattr(test_case, "expected") and test_case.expected:
                    expected_match = await check_expected_text(page, test_case.expected)

                validation_payload = {
                    "url_changed": url_changed,
                    "error_detected": error_detected,
                    "title": snapshot["title"],
                    "url": snapshot["url"],
                    "expected_matched": expected_match,
                    "console_errors": list(console_errors),
                    "network_failures": list(network_failures),
                }

                recovery_info = {
                    "recovery_attempted": False,
                    "recovery_success": False,
                    "recovery_type": "",
                    "recovery_actions": [],
                    "error": "",
                    "validation": None,
                }

                if status == "failed":
                    recovery_info = await _safe_attempt_step_recovery(
                        page,
                        action_lower=action_lower,
                        step=step,
                        selector=selector,
                        selector_hint=selector_hint,
                        typed_value=typed_value,
                        dom=dom,
                        url=url,
                        previous_url=previous_url,
                        test_case=test_case,
                        progress_callback=progress_callback,
                        error_text="",
                        validation=validation_payload,
                    )
                    if recovery_info.get("recovery_success") and recovery_info.get("validation"):
                        validation_result = recovery_info["validation"]
                        url_changed = validation_result["url_changed"]
                        error_detected = validation_result["error_detected"]
                        snapshot = validation_result["snapshot"]
                        expected_match = validation_result["expected_match"]
                        validation_payload = {
                            "url_changed": url_changed,
                            "error_detected": error_detected,
                            "title": snapshot["title"],
                            "url": snapshot["url"],
                            "expected_matched": expected_match,
                            "console_errors": list(console_errors),
                            "network_failures": list(network_failures),
                        }

                status = _resolve_step_final_status(
                    action_lower=action_lower,
                    recovery_info=recovery_info,
                    validation_payload=validation_payload,
                    test_case=test_case,
                )

                failure_category = None
                root_cause_result = {"root_cause": None, "confidence": None}
                verification_mismatch = action_lower == "verify" and status == "failed"
                if status == "failed":
                    failure_category = classify_failure_category(
                        error_text=recovery_info.get("error") or "",
                        console_errors=console_errors,
                        network_failures=network_failures,
                        step_text=f"{action} {target} {selector} {display_name}",
                        selector=selector,
                        target=target,
                        test_name=getattr(test_case, "title", ""),
                        validation=validation_payload,
                    )
                    root_cause_result = classify_root_cause(
                        action=action,
                        category=failure_category,
                        error=recovery_info.get("error") or "",
                        console_errors=console_errors,
                        network_failures=network_failures,
                        selector_used=selector,
                        validation=validation_payload,
                    )

                results.append({
                    "step": step.model_dump(),
                    "selector_used": selector,
                    "status": status,
                    "error": recovery_info.get("error") if status == "failed" else None,
                    "details": (recovery_info.get("recovery_hint") or "Step validation failed.") if status == "failed" else None,
                    "failure_category": failure_category if status == "failed" else None,
                    "root_cause": root_cause_result["root_cause"] if status == "failed" else None,
                    "root_cause_confidence": root_cause_result["confidence"] if status == "failed" else None,
                    "recovery_attempted": recovery_info.get("recovery_attempted", False),
                    "recovery_type": recovery_info.get("recovery_type") or None,
                    "recovery_success": recovery_info.get("recovery_success", False),
                    "recovery_actions": recovery_info.get("recovery_actions", []),
                    "recovery_error": recovery_info.get("recovery_error") or (recovery_info.get("error") if recovery_info.get("recovery_attempted") and not recovery_info.get("recovery_success") else None),
                    "recovery_hint": "; ".join(item.get("detail", "") for item in recovery_info.get("recovery_actions", []) if item.get("detail")) or None,
                    "validation": validation_payload,
                    "execution_context": step_execution_context,
                    "selector_fallback_used": selector_fallback_used,
                    "verification_mismatch": verification_mismatch,
                })
                logger.info(
                    "Step %d/%d result: action=%s status=%s results_so_far=%d",
                    step_index,
                    total_steps_for_log,
                    action,
                    status,
                    len(results),
                )
                if status == "passed" and selector:
                    try:
                        record_selector_success(
                            selector,
                            target or selector_hint or selector,
                            context={
                                "page_url": snapshot.get("url") or page.url,
                                "url": snapshot.get("url") or page.url,
                                "current_url": snapshot.get("url") or page.url,
                                "feature_key": getattr(test_case, "feature_key", None),
                                "objective_name": getattr(test_case, "objective_name", None),
                                "scenario_name": getattr(test_case, "scenario_name", None),
                            },
                            action=action_lower,
                            source="execution_success",
                        )
                    except Exception:
                        pass

                if status == "passed":
                    previous_successful_actions.append(f"{action_lower}:{display_name}")
                if any(keyword in (display_name or "").lower() for keyword in ["login", "sign in", "sign-in", "authenticate"]) and status == "passed":
                    authenticated = True

                # Emit a single timeline entry for the completed step with its final status.
                await _emit_progress(progress_callback, {
                    "type": "timeline_step",
                    "message": f"Step finished: {action}",
                    "step": step.model_dump(),
                    "status": status,
                    "execution_context": step_execution_context,
                })
                await _emit_progress(progress_callback, {
                    "type": "step_completed",
                    "message": f"Completed step {step_index}/{total_steps_for_log}: {action or 'action'} -> {status}",
                    "step": step.model_dump(),
                    "status": status,
                    "step_index": step_index,
                    "total_steps": total_steps_for_log,
                    "scenario_id": getattr(test_case, "scenario_id", None),
                    "scenario_name": getattr(test_case, "scenario_name", None),
                })

                previous_url = page.url

                if status == "failed":
                    # Emit a bug record for failures (separate from timeline).
                    await _emit_progress(progress_callback, {
                        "type": "bug_detected",
                        "message": f"Step failed: {action}",
                        "step": step.model_dump(),
                        "error": recovery_info.get("error") or "Step failed after recovery attempts",
                        "recovery_attempted": recovery_info.get("recovery_attempted", False),
                        "recovery_success": recovery_info.get("recovery_success", False),
                        "recovery_type": recovery_info.get("recovery_type") or None,
                    })

            except Exception as e:
                await _capture_step_screenshot(page, step, progress_callback, label="after_failure")
                recovery_info = await _safe_attempt_step_recovery(
                    page,
                    action_lower=action_lower,
                    step=step,
                    selector=selector,
                    selector_hint=selector_hint,
                    typed_value=typed_value,
                    dom=dom,
                    url=url,
                    previous_url=previous_url,
                    test_case=test_case,
                    progress_callback=progress_callback,
                    error_text=str(e),
                    validation={
                        "console_errors": list(console_errors),
                        "network_failures": list(network_failures),
                    },
                )

                if recovery_info.get("recovery_success") and recovery_info.get("validation"):
                    validation_result = recovery_info["validation"]
                    status = _resolve_step_final_status(
                        action_lower=action_lower,
                        recovery_info={"recovery_success": True},
                        validation_payload=validation_result,
                        test_case=test_case,
                    )
                    results.append({
                        "step": step.model_dump(),
                        "selector_used": selector,
                        "status": status,
                        "failure_category": None,
                        "root_cause": None,
                        "root_cause_confidence": None,
                        "recovery_attempted": True,
                        "recovery_type": recovery_info.get("recovery_type") or None,
                        "recovery_success": True,
                        "recovery_actions": recovery_info.get("recovery_actions", []),
                        "recovery_error": None,
                        "recovery_hint": "; ".join(item.get("detail", "") for item in recovery_info.get("recovery_actions", []) if item.get("detail")) or None,
                        "validation": {
                            "url_changed": validation_result["url_changed"],
                            "error_detected": validation_result["error_detected"],
                            "title": validation_result["snapshot"]["title"],
                            "url": validation_result["snapshot"]["url"],
                            "expected_matched": validation_result["expected_match"],
                            "console_errors": list(console_errors),
                            "network_failures": list(network_failures),
                        },
                        "execution_context": step_execution_context,
                        "selector_fallback_used": selector_fallback_used,
                        "verification_mismatch": action_lower == "verify" and status == "failed",
                    })
                    logger.info(
                        "Step %d/%d result (recovered): action=%s status=%s results_so_far=%d",
                        step_index,
                        total_steps_for_log,
                        action,
                        status,
                        len(results),
                    )
                    await _emit_progress(progress_callback, {
                        "type": "timeline_step",
                        "message": f"Recovered step: {action}",
                        "step": step.model_dump(),
                        "status": "passed",
                        "recovery_type": recovery_info.get("recovery_type") or None,
                    })
                    await _emit_progress(progress_callback, {
                        "type": "step_completed",
                        "message": f"Completed step {step_index}/{total_steps_for_log}: {action or 'action'} -> {status} after recovery",
                        "step": step.model_dump(),
                        "status": status,
                        "step_index": step_index,
                        "total_steps": total_steps_for_log,
                        "scenario_id": getattr(test_case, "scenario_id", None),
                        "scenario_name": getattr(test_case, "scenario_name", None),
                        "recovery_type": recovery_info.get("recovery_type") or None,
                    })
                    previous_url = page.url
                    continue

                failure_category = classify_failure_category(
                    error_text=str(e),
                    console_errors=console_errors,
                    network_failures=network_failures,
                    step_text=f"{action} {target} {selector} {display_name}",
                    selector=selector,
                    target=target,
                    test_name=getattr(test_case, "title", ""),
                    validation={
                        "console_errors": list(console_errors),
                        "network_failures": list(network_failures),
                    },
                )
                root_cause_result = classify_root_cause(
                    action=action,
                    category=failure_category,
                    error=str(e),
                    console_errors=console_errors,
                    network_failures=network_failures,
                    selector_used=selector,
                    validation={
                        "console_errors": list(console_errors),
                        "network_failures": list(network_failures),
                    },
                )
                status = "failed"
                results.append({
                    "step": step.model_dump(),
                    "selector_used": selector,
                    "status": status,
                    "error": str(e),
                    "details": recovery_info.get("recovery_hint") or str(e),
                    "failure_category": failure_category,
                    "root_cause": root_cause_result["root_cause"],
                    "root_cause_confidence": root_cause_result["confidence"],
                    "recovery_attempted": recovery_info.get("recovery_attempted", False),
                    "recovery_type": recovery_info.get("recovery_type") or None,
                    "recovery_success": recovery_info.get("recovery_success", False),
                    "recovery_actions": recovery_info.get("recovery_actions", []),
                    "recovery_error": recovery_info.get("recovery_error") or recovery_info.get("error") or str(e),
                    "recovery_hint": "; ".join(item.get("detail", "") for item in recovery_info.get("recovery_actions", []) if item.get("detail")) or None,
                    "validation": {
                        "console_errors": list(console_errors),
                        "network_failures": list(network_failures),
                    },
                    "execution_context": step_execution_context,
                    "selector_fallback_used": selector_fallback_used,
                    "verification_mismatch": action_lower == "verify" and status == "failed",
                })
                logger.info(
                    "Step %d/%d result (exception): action=%s status=%s results_so_far=%d error=%s",
                    step_index,
                    total_steps_for_log,
                    action,
                    status,
                    len(results),
                    str(e)[:120],
                )
                await _emit_progress(progress_callback, {
                    "type": "bug_detected",
                    "message": f"Step failed: {action}",
                    "step": step.model_dump(),
                    "error": str(e),
                })
                await _emit_progress(progress_callback, {
                    "type": "step_failed",
                    "message": f"Failed step {step_index}/{total_steps_for_log}: {action or 'action'} -> {str(e)[:160]}",
                    "step": step.model_dump(),
                    "error": str(e),
                    "step_index": step_index,
                    "total_steps": total_steps_for_log,
                    "scenario_id": getattr(test_case, "scenario_id", None),
                    "scenario_name": getattr(test_case, "scenario_name", None),
                })
                previous_url = page.url

        logger.info(
            "Step loop finished: scenario=%s  expected=%d  executed=%d  skipped=%d",
            scenario_label_for_log,
            total_steps_for_log,
            len(results),
            max(0, total_steps_for_log - len(results)),
        )
        final_url = page.url
        try:
            final_title = await page.title()
        except Exception:
            final_title = ""
        try:
            artifacts_state = await context.storage_state()
            storage_root = Path(__file__).resolve().parents[2] / "artifacts" / "storage_state"
            storage_root.mkdir(parents=True, exist_ok=True)
            parsed_url = urlparse(final_url or url or "")
            domain = (parsed_url.hostname or "session").lower()
            feature_key = _normalize_text(getattr(test_case, "feature_key", None)) or "global"
            scenario_name = _normalize_text(getattr(test_case, "scenario_name", None) or getattr(test_case, "title", None)) or "scenario"
            safe_name = "_".join(part for part in [domain, feature_key, scenario_name] if part)
            safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in safe_name).strip("_") or "session"
            storage_state_path = storage_root / f"{safe_name}.json"
            await context.storage_state(path=str(storage_state_path))
            storage_state_result = str(storage_state_path)
        except Exception:
            storage_state_result = None
        try:
            session_storage = await page.evaluate("() => Object.fromEntries(Object.entries(sessionStorage))")
        except Exception:
            session_storage = {}
        await _cleanup_runtime_resources("execution-complete")
        metrics = _build_execution_metrics(len(steps_to_run), results)
        if metrics["skipped_tasks"] > 0:
            logger.warning(
                "Incomplete step execution: scenario=%s  expected=%d  executed=%d  skipped=%d",
                scenario_label_for_log,
                total_steps_for_log,
                metrics["completed_tasks"] + metrics["failed_tasks"],
                metrics["skipped_tasks"],
            )
            run_status = "failed"
        else:
            run_status = "completed_with_failures" if metrics["failed_tasks"] else "completed"
        await _emit_progress(progress_callback, {
            "type": "run_status",
            "message": f"Scenario finished: {test_case.title or test_case.scenario_name or 'untitled'}",
            "status": run_status,
            **metrics,
        })

        return {
            "url": url,
            "final_url": final_url,
            "page_title": final_title,
            "total_steps": metrics["total_tasks"],
            "results": results,
            "run_status": run_status,
            "artifacts": {
                "storage_state": storage_state_result,
                "session_storage": session_storage,
                "previous_successful_actions": previous_successful_actions,
                "authenticated": authenticated,
            },
            **metrics,
        }

    except asyncio.CancelledError as exc:
        logger.warning("Playwright execution cancelled; returning partial results", exc_info=False)
        partial_results = list(locals().get("results", []))
        total_steps = len(locals().get("steps_to_run", list(getattr(test_case, "steps", []) or [])))
        logger.warning(
            "CancelledError: scenario=%s  expected_steps=%d  collected_results=%d",
            getattr(test_case, "scenario_id", None) or getattr(test_case, "scenario_name", "?"),
            total_steps,
            len(partial_results),
        )
        try:
            await _cleanup_runtime_resources("cancelled")
        except Exception:
            logger.exception("Cleanup failed after cancellation")

        metrics = _build_execution_metrics(total_steps, partial_results)
        run_status = "timed_out"
        await _emit_progress(progress_callback, {
            "type": "run_status",
            "message": f"Scenario cancelled or timed out: {test_case.title or test_case.scenario_name or 'untitled'}; partial results preserved",
            "status": run_status,
            **metrics,
        })
        return {
            "url": url,
            "total_steps": metrics["total_tasks"],
            "results": partial_results,
            "run_status": run_status,
            "status": "timed_out",
            "failure_reason": "execution_cancelled_or_timed_out",
            **metrics,
        }

    except Exception as exc:
        # Capture and emit the exception/traceback for diagnostics before failing
        tb = traceback.format_exc()
        logger.exception("Playwright execution failed", exc_info=exc)
        await _emit_progress(progress_callback, {
            "type": "run_error", 
            "message": "REAL_EXECUTION_FAILED: Playwright execution failed. FALLBACK_BLOCKED.", 
            "error": str(exc), 
            "traceback": tb
        })

        metrics = _build_execution_metrics(len(steps_to_run) if 'steps_to_run' in locals() else len(test_case.steps), [])
        total_steps = len(steps_to_run) if 'steps_to_run' in locals() else len(test_case.steps)
        metrics["failed_tasks"] = total_steps
        metrics["skipped_tasks"] = total_steps
        metrics["completed_tasks"] = 0
        run_status = "failed"

        try:
            await _cleanup_runtime_resources("error")
        except Exception:
            logger.exception("Cleanup failed after execution error")

        await _emit_progress(progress_callback, {"type": "run_status", "message": f"Scenario finished with failures: {test_case.title or test_case.scenario_name or 'untitled'}", "status": run_status, **metrics})
        
        return {
            "url": url, 
            "total_steps": metrics["total_tasks"], 
            "results": [], 
            "run_status": run_status, 
            "status": "failed",
            "failure_reason": "playwright_execution_failed",
            "error": str(exc),
            "traceback": tb,
            **metrics
        }

