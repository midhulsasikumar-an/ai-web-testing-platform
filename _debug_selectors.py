"""Debug script: count all .max-w-[92%].rounded-xl elements and see where they come from."""
from playwright.sync_api import sync_playwright
import time
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.set_default_timeout(15000)

    # Login
    page.goto("http://127.0.0.1:3000/login", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.fill('input[type="email"]', "playwright_4b1cd045@example.com")
    page.fill('input[type="password"]', "Test1234!")
    with page.expect_navigation(timeout=20000):
        page.click('button[type="submit"]')
    print("Login OK")

    # Navigate to /test-history/e5a2bae7-4e92-46c4-98b8-910c1a5edd74 to see the existing completed test
    page.goto("http://127.0.0.1:3000/run-test", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)

    # Count all matching elements
    info = page.evaluate("""() => {
        const els = document.querySelectorAll('div.max-w-\\\\[92\\\\%\\\\].rounded-xl');
        const sample = [];
        for (let i = 0; i < Math.min(5, els.length); i++) {
            const el = els[i];
            const parent = el.parentElement;
            sample.push({
                text: (el.textContent || '').trim().slice(0, 100),
                parentClass: parent ? parent.className : '?',
                grandparentClass: parent && parent.parentElement ? parent.parentElement.className.slice(0, 100) : '?',
                rect: el.getBoundingClientRect(),
            });
        }
        return { count: els.length, sample };
    }""")
    print(f"Total elements with .max-w-[92%].rounded-xl: {info['count']}")
    print("Sample:")
    for s in info["sample"]:
        print(f"  text={s['text']!r}")
        print(f"    parent class: {s['parentClass']!r}")
        print(f"    grandparent class: {s['grandparentClass']!r}")
        print(f"    rect: x={s['rect']['x']:.0f} y={s['rect']['y']:.0f} w={s['rect']['width']:.0f} h={s['rect']['height']:.0f}")

    browser.close()
