import asyncio

from playwright.async_api import Page

DEFAULT_VALIDATION_TIMEOUT = 5000


async def _timed_validation(coro, timeout_ms: int = DEFAULT_VALIDATION_TIMEOUT):
    return await asyncio.wait_for(coro, timeout=timeout_ms / 1000)

SUCCESS_KEYWORDS = [
    "success",
    "welcome",
    "dashboard",
    "home",
    "overview",
    "logged in",
    "completed",
    "saved",
    "account",
    "profile",
    "authenticated",
    # Include ecommerce/inventory keywords to help detect inventory pages
    "product",
    "products",
    "inventory",
    "catalog",
]

ERROR_KEYWORDS = [
    "invalid",
    "incorrect",
    "required",
    "failed",
    "error",
    "try again"
]

SUCCESS_SHELL_SELECTORS = [
    "main",
    "[role='main']",
    "nav",
    "header",
    "[role='navigation']",
    "[aria-label*='dashboard' i]",
    "[data-testid*='dashboard' i]",
    "[data-test*='dashboard' i]",
]

SAUCEDMO_SUCCESS_SELECTORS = [
    ".inventory_list",
    ".shopping_cart_link",
    ".shopping_cart_badge",
    ".cart_list",
    "#checkout",
    "#first-name",
    "#last-name",
    "#postal-code",
    "#continue",
    "#finish",
    ".complete-header",
]

async def check_url_change(page: Page, previous_url: str):
    return page.url != previous_url


async def check_error_messages(page: Page):
    error_selectors = [
        ".error",
        ".alert",
        ".toast-error",
        "[role='alert']",
        ".flash-error"
    ]

    for sel in error_selectors:
        if await _timed_validation(page.locator(sel).count()):
            return True

    return False


async def check_expected_text(page: Page, expected: str):
    content = await _timed_validation(page.inner_text("body"))
    return expected.lower() in content.lower()


async def detect_success_state(page: Page, previous_url: str = None):
    url = (page.url or "").lower()
    title = (await _timed_validation(page.title())).lower()
    body = (await _timed_validation(page.inner_text("body"))).lower()

    if any(path in url for path in ["/inventory.html", "/cart.html", "/checkout-step-one.html", "/checkout-step-two.html", "/checkout-complete.html"]):
        return True

    try:
        for selector in SAUCEDMO_SUCCESS_SELECTORS:
            if await _timed_validation(page.locator(selector).count()):
                return True
    except Exception:
        pass

    if previous_url and page.url != previous_url:
        if not any(keyword in body for keyword in ERROR_KEYWORDS):
            return True

    if any(keyword in title for keyword in SUCCESS_KEYWORDS):
        return True

    if any(keyword in body for keyword in SUCCESS_KEYWORDS):
        return True

    try:
        for selector in SUCCESS_SHELL_SELECTORS:
            if await _timed_validation(page.locator(selector).count()):
                return True
    except Exception:
        pass

    if any(keyword in url for keyword in ["dashboard", "/home", "/app", "/account", "/profile"]) and "login" not in url:
        return True

    return False


async def detect_login_success(page: Page):
    return await detect_success_state(page)


async def get_page_snapshot(page: Page):
    return {
        "title": await _timed_validation(page.title()),
        "url": page.url
    }

async def detect_page_state(page):

    content = (await _timed_validation(page.content())).lower()

    success_found = any(word in content for word in SUCCESS_KEYWORDS)
    error_found = any(word in content for word in ERROR_KEYWORDS)

    return {
        "success_detected": success_found,
        "error_detected": error_found
    }