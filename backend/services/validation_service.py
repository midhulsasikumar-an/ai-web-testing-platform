from playwright.async_api import Page


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