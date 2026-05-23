from playwright.async_api import Page

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
    "authenticated"
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
        if await page.locator(sel).count() > 0:
            return True

    return False


async def check_expected_text(page: Page, expected: str):
    content = await page.inner_text("body")
    return expected.lower() in content.lower()


async def detect_success_state(page: Page, previous_url: str = None):
    url = (page.url or "").lower()
    title = (await page.title()).lower()
    body = (await page.inner_text("body")).lower()

    if previous_url and page.url != previous_url:
        if not any(keyword in body for keyword in ERROR_KEYWORDS):
            return True

    if any(keyword in title for keyword in SUCCESS_KEYWORDS):
        return True

    if any(keyword in body for keyword in SUCCESS_KEYWORDS):
        return True

    try:
        for selector in SUCCESS_SHELL_SELECTORS:
            if await page.locator(selector).count() > 0:
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
        "title": await page.title(),
        "url": page.url
    }

async def detect_page_state(page):

    content = (await page.content()).lower()

    success_found = any(word in content for word in SUCCESS_KEYWORDS)
    error_found = any(word in content for word in ERROR_KEYWORDS)

    return {
        "success_detected": success_found,
        "error_detected": error_found
    }