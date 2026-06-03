from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.set_default_timeout(15000)
    # Login
    page.goto("http://127.0.0.1:3000/login", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.fill('input[type="email"]', "playwright_2e5ba2f3@example.com")
    page.fill('input[type="password"]', "Test1234!")
    with page.expect_navigation(timeout=20000):
        page.click('button[type="submit"]')
    print("Login OK, URL:", page.url)
    # Navigate to run-test
    page.goto("http://127.0.0.1:3000/run-test", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    h2s = page.locator("h2").all_text_contents()
    print("h2s on run-test page:", h2s)
    body = page.locator("body").inner_text()
    if "AI Copilot" in body:
        idx = body.index("AI Copilot")
        print("--- snippet around AI Copilot (2000 chars) ---")
        print(body[max(0, idx-50):idx+2000])
    else:
        print("AI Copilot not in body text")
    if "Execution Terminal" in body:
        idx = body.index("Execution Terminal")
        print("--- snippet around Execution Terminal (2000 chars) ---")
        print(body[max(0, idx-50):idx+2000])
    else:
        print("Execution Terminal not in body text")
    browser.close()
