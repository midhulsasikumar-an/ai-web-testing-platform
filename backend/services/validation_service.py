from playwright.async_api import Page

SUCCESS_KEYWORDS = [
    "success",
    "welcome",
    "dashboard",
    "logged in",
    "completed",
    "saved"
]

ERROR_KEYWORDS = [
    "invalid",
    "incorrect",
    "required",
    "failed",
    "error",
    "try again"
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