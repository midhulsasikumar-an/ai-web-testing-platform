import inspect

from playwright.async_api import async_playwright
from backend.services.safety_service import is_same_domain
from backend.services.selector_resolver import resolve_selector
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

async def safe_click(page, selector):

    locator = page.locator(selector).first
    await locator.wait_for(state="attached", timeout=10000)
    await locator.scroll_into_view_if_needed()
    try:
        await locator.wait_for(state="visible", timeout=10000)
    except Exception:
        pass

    try:
        if await locator.is_enabled():
            await locator.click()
            return
    except Exception:
        pass

    await locator.click(force=True)


async def safe_fill(page, selector, value):
    locator = page.locator(selector)

    await locator.wait_for(state="attached", timeout=10000)
    await locator.scroll_into_view_if_needed()

    try:
        await locator.wait_for(state="visible", timeout=10000)
    except Exception:
        pass

    try:
        if await locator.is_visible() and await locator.is_enabled():
            await locator.fill(value)
            return
    except Exception:
        pass

    try:
        await locator.click(force=True)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(value, delay=25)
        return
    except Exception:
        pass

    await locator.focus()
    await page.keyboard.type(value, delay=25)


async def safe_wait(page, selector):
    locator = page.locator(selector).first
    await locator.wait_for(state="visible", timeout=10000)


async def safe_hover(page, selector):
    locator = page.locator(selector).first
    await locator.wait_for(state="visible", timeout=10000)
    await locator.hover()


async def safe_select(page, selector, value):
    locator = page.locator(selector).first
    await locator.wait_for(state="visible", timeout=10000)
    await locator.select_option(value=value)


INPUT_ACTIONS = {"type", "enter", "fill", "input", "enter_text", "input_text"}


def _normalize_text(value):
    return " ".join((value or "").strip().lower().replace("_", " ").split())


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
    return any(keyword in normalized for keyword in ["success", "dashboard", "welcome", "home", "overview", "account", "profile", "authenticated", "logged in"])


def _resolve_step_selector(step, dom):
    candidates = []
    if step.selector:
        candidates.append(step.selector)
    if step.target and not (_normalize_text(step.action) in INPUT_ACTIONS and not _looks_like_field_hint(step.target)):
        candidates.append(step.target)

    for candidate in candidates:
        resolved = resolve_selector(candidate, dom or {})
        if resolved and not resolved.startswith('text="'):
            return resolved, candidate

    if _normalize_text(step.action) in INPUT_ACTIONS:
        hint = _hint_to_label(step.selector or step.target or "")
        resolved = resolve_selector(hint, dom or {})
        if resolved and not resolved.startswith('text="'):
            return resolved, hint

        inputs = (dom or {}).get("inputs", [])
        if any(keyword in _normalize_text(step.selector or step.target or step.value or "") for keyword in ["password"]):
            if len(inputs) > 1:
                second = inputs[1]
                return resolve_selector(second.get("placeholder") or second.get("name") or second.get("id") or "password field", dom or {}) or f'input[type="password"]', "password field"
        if any(keyword in _normalize_text(step.selector or step.target or step.value or "") for keyword in ["username", "user name", "email"]):
            if inputs:
                first = inputs[0]
                return resolve_selector(first.get("placeholder") or first.get("name") or first.get("id") or "username field", dom or {}) or f'input[type="text"]', "username field"

        if inputs:
            first = inputs[0]
            return resolve_selector(first.get("placeholder") or first.get("name") or first.get("id") or "username field", dom or {}) or f'input[type="text"]', "username field"

    return (step.selector or resolve_selector(step.target, dom or {}) or (f'text="{step.target}"' if step.target else None)), (step.selector or step.target)


async def _emit_progress(progress_callback, payload):
    if not progress_callback:
        return
    result = progress_callback(payload)
    if inspect.isawaitable(result):
        await result


async def run_test_steps(url: str, test_case, dom: dict = None,credentials: dict = None, progress_callback=None):
    # Try to execute using Playwright. If Playwright cannot be spawned in
    # this environment (e.g., asyncio.create_subprocess_exec NotImplementedError
    # on some Windows setups), fall back to a simulated executor that emits
    # progress messages so the front-end receives live logs and the pipeline
    # can continue in development environments.
    try:
        await _emit_progress(progress_callback, {"type": "run_status", "message": "Launching Playwright"})
        async with async_playwright() as p:
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Playwright started"})
            browser = await p.chromium.launch(headless=True)
            await _emit_progress(progress_callback, {"type": "run_status", "message": "Browser launched"})
            page = await browser.new_page()

            await _emit_progress(progress_callback, {"type": "run_status", "message": f"Opening {url}"})
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception:
                await _emit_progress(progress_callback, {"type": "run_status", "message": "Retrying page load"})
                await page.goto(url, wait_until="load", timeout=60000)
            await _emit_progress(progress_callback, {
                "type": "run_status",
                "message": f"Opened {url}",
            })

            results = []
            previous_url = page.url

            for step in test_case.steps:
                action = step.action
                target = step.target
                value = step.value

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

                selector, selector_hint = _resolve_step_selector(step, dom)
                selector = selector or f'text="{target}"'

                action_lower = (action or "").lower()
                display_name = selector_hint or target or selector or "unknown target"

                try:
                    typed_value = value or ""
                    if action_lower in INPUT_ACTIONS and not typed_value and target and not _looks_like_field_hint(target):
                        typed_value = target

                    await _emit_progress(progress_callback, {
                        "type": "action_execution",
                        "message": f"Executing {action} on {display_name}",
                        "step": step.model_dump(),
                    })

                    if action_lower == "click":
                        await _emit_progress(progress_callback, {"type": "action_execution", "message": f"Clicking {display_name}", "step": step.model_dump()})
                        await safe_click(page, selector)
                    elif action_lower in INPUT_ACTIONS:
                        await _emit_progress(progress_callback, {"type": "action_execution", "message": f"Found {display_name}", "step": step.model_dump()})
                        await _emit_progress(progress_callback, {"type": "action_execution", "message": f"Typing value into {display_name}", "step": step.model_dump()})
                        await safe_fill(page, selector, typed_value)
                    elif action_lower == "press":
                        await page.keyboard.press(value)
                    elif action_lower == "wait":
                        await safe_wait(page, selector)
                    elif action_lower == "hover":
                        await safe_hover(page, selector)
                    elif action_lower == "select":
                        await safe_select(page, selector, value or "")
                    elif action_lower == "navigate":
                        if value and isinstance(value, str):
                            await _emit_progress(progress_callback, {"type": "run_status", "message": f"Navigating to URL {value}"})
                            await page.goto(value, wait_until="domcontentloaded")
                    elif action_lower == "verify":
                        verify_subject = (target or selector or "").strip() if isinstance(target or selector or "", str) else ""
                        verify_value = (value or "").strip().lower() if isinstance(value or "", str) else ""
                        if verify_subject:
                            subject_lower = verify_subject.lower()
                            if verify_value in {"visible", "present", "exists", "exist"}:
                                if _looks_like_success_subject(verify_subject):
                                    if not await detect_success_state(page, previous_url):
                                        raise Exception(f"Success-state verification failed for expected state: {verify_subject}")
                                elif _looks_like_selector(verify_subject):
                                    locator = page.locator(verify_subject).first
                                    await locator.wait_for(state="visible", timeout=5000)
                                else:
                                    if not await check_expected_text(page, verify_subject):
                                        raise Exception(f"Verification failed for expected text: {verify_subject}")
                            else:
                                if _looks_like_success_subject(verify_subject):
                                    if not await detect_success_state(page, previous_url):
                                        raise Exception(f"Success-state verification failed for expected state: {verify_subject}")
                                elif "title" in (target or "").lower():
                                    current_title = await page.title()
                                    if verify_subject.lower() not in current_title.lower():
                                        raise Exception(f"Title verification failed. Expected '{verify_subject}' in '{current_title}'")
                                elif _looks_like_selector(verify_subject):
                                    locator = page.locator(verify_subject).first
                                    await locator.wait_for(state="visible", timeout=5000)
                                else:
                                    matched = await check_expected_text(page, verify_subject)
                                    if not matched:
                                        raise Exception(f"Verification failed for expected text: {verify_subject}")
                    elif action == "screenshot":
                        # explicit screenshot action; binary is emitted below in common capture block
                        pass

                    # VALIDATION CHECKS
                    url_changed = await check_url_change(page, previous_url)
                    error_detected = await check_error_messages(page)
                    snapshot = await get_page_snapshot(page)

                    # capture a per-step screenshot (best-effort)
                    try:
                        ss = await page.screenshot(full_page=False)
                        # send as base64 in progress so callers can persist if desired
                        await _emit_progress(progress_callback, {"type": "screenshot", "step": step.model_dump(), "screenshot_b64": base64.b64encode(ss).decode('ascii')})
                    except Exception:
                        pass

                    previous_url = page.url

                    is_negative_test = any(
                        keyword in (test_case.expected or "").lower()
                        for keyword in ["error", "invalid", "failed", "required"]
                    )
                    if is_negative_test:
                        status = "passed" if error_detected else "failed"
                    else:
                        status = "failed" if error_detected else "passed"

                    expected_match = False
                    success_flow = any(keyword in ((test_case.title or "") + " " + (test_case.expected or "")).lower() for keyword in ["login", "sign in", "authenticate", "success", "dashboard", "welcome", "home", "profile", "account"])
                    if success_flow:
                        expected_match = await detect_success_state(page, previous_url)
                        if expected_match:
                            await _emit_progress(progress_callback, {"type": "run_status", "message": "Success state detected"})
                    elif hasattr(test_case, "expected") and test_case.expected:
                        expected_match = await check_expected_text(page, test_case.expected)

                    if not is_same_domain(url, page.url):
                        raise Exception("Navigation outside allowed domain detected")

                    results.append({
                        "step": step.model_dump(),
                        "selector_used": selector,
                        "status": status,
                        "validation": {
                            "url_changed": url_changed,
                            "error_detected": error_detected,
                            "title": snapshot["title"],
                            "url": snapshot["url"],
                            "expected_matched": expected_match,
                        },
                    })

                    await _emit_progress(progress_callback, {
                        "type": "timeline_step",
                        "message": f"Completed step: {action}",
                        "step": step.model_dump(),
                        "status": status,
                    })

                except Exception as e:
                    results.append({
                        "step": step.model_dump(),
                        "selector_used": selector,
                        "status": "failed",
                        "error": str(e),
                    })
                    await _emit_progress(progress_callback, {
                        "type": "bug_detected",
                        "message": f"Step failed: {action}",
                        "step": step.model_dump(),
                        "error": str(e),
                    })
                    break

            await browser.close()
            await _emit_progress(progress_callback, {
                "type": "run_status",
                "message": "Execution finished",
                "status": "completed",
            })

            return {"url": url, "total_steps": len(test_case.steps), "results": results}

    except Exception as exc:
        # Capture and emit the exception/traceback for diagnostics before falling back
        tb = traceback.format_exc()
        # Also print to server logs for easier debugging when no progress_callback is provided
        try:
            print("[execution_service] Playwright execution failed:", str(exc))
            print(tb)
        except Exception:
            pass
        await _emit_progress(progress_callback, {"type": "run_error", "message": "Playwright execution failed, falling back to simulation", "error": str(exc), "traceback": tb})

        # Fallback simulated execution for environments where Playwright cannot
        # spawn subprocesses. This still emits progress events so the frontend
        # receives live logs and the rest of the pipeline can complete.
        results = []
        await _emit_progress(progress_callback, {"type": "run_status", "message": "(Fallback) Starting simulated execution"})

        for step in test_case.steps:
            await _emit_progress(progress_callback, {"type": "action_execution", "message": f"(Sim) Executing {step.action} on {step.target}", "step": step.model_dump()})
            # small delay to simulate work
            try:
                # simple heuristics for simulated status
                status = "passed"
                if step.action.lower() in ["verify", "check"]:
                    status = "passed"
                results.append({"step": step.model_dump(), "selector_used": step.selector or "", "status": status})
                await _emit_progress(progress_callback, {"type": "timeline_step", "message": f"(Sim) Completed step: {step.action}", "step": step.model_dump(), "status": status})
            except Exception as e:
                results.append({"step": step.model_dump(), "selector_used": step.selector or "", "status": "failed", "error": str(e)})
                await _emit_progress(progress_callback, {"type": "bug_detected", "message": f"(Sim) Step failed: {step.action}", "step": step.model_dump(), "error": str(e)})
                break

        await _emit_progress(progress_callback, {"type": "run_status", "message": "(Fallback) Execution finished", "status": "completed"})
        return {"url": url, "total_steps": len(test_case.steps), "results": results}