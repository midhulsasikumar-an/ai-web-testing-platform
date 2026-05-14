from playwright.async_api import async_playwright
from backend.services.safety_service import is_same_domain
from backend.services.selector_resolver import resolve_selector
from backend.services.validation_service import (
    check_expected_text,
    check_url_change,
    check_error_messages,
    get_page_snapshot
)


async def safe_click(page, selector):
    locator = page.locator(selector)

    await locator.wait_for(timeout=5000)
    await locator.scroll_into_view_if_needed()
    await locator.click()


async def safe_fill(page, selector, value):
    locator = page.locator(selector)

    await locator.wait_for(timeout=5000)
    await locator.scroll_into_view_if_needed()
    await locator.fill(value)


async def run_test_steps(url: str, test_case, dom: dict = None):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded")

        results = []
        previous_url = page.url

        for step in test_case.steps:

            action = step.action
            target = step.target
            value = step.value

            selector = step.selector or resolve_selector(target, dom or {}) or f"text={target}"

            try:
                if action == "click":
                    await safe_click(page, selector)

                elif action in ["type", "enter", "fill"]:
                    await safe_fill(page, selector, value or "")

                elif action == "press":
                    await page.keyboard.press(value)

                # VALIDATION CHECKS
                url_changed = await check_url_change(page, previous_url)
                error_detected = await check_error_messages(page)
                snapshot = await get_page_snapshot(page)

                previous_url = page.url
                if error_detected:
                    status = "failed"
                elif action == "click" and not url_changed:
                    status = "warning"
                else:                   
                    status = "passed"

                expected_match = False

                if hasattr(test_case, "expected") and test_case.expected:
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
                        "expected_matched": expected_match
                    }
                })

            except Exception as e:
                results.append({
                    "step": step.model_dump(),
                    "selector_used": selector,
                    "status": "failed",
                    "error": str(e)
                })
                break

        await browser.close()

        return {
            "url": url,
            "total_steps": len(test_case.steps),
            "results": results
        }