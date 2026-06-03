"""
Fix-B regression check.

Verifies that during a real test run, the AI Copilot chat does NOT accumulate
duplicate "Execution status:" messages.

Strategy: same as _validation_run.py — sign up a fresh user, force the AI plan
path via route interception, start a test, capture chat message counts at
three checkpoints (idle, running, terminal).
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

ROOT = Path(r"C:\Internship\ai-testing-platform")
EVIDENCE = ROOT / "_validation_fix_b"
EVIDENCE.mkdir(parents=True, exist_ok=True)
LOG_PATH = EVIDENCE / "console.log"
REPORT_PATH = EVIDENCE / "REPORT.json"
FRONTEND = "http://127.0.0.1:3000"
API = "http://127.0.0.1:8001"

console_lines: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    console_lines.append(line)


async def attach_console(page: Page) -> None:
    def on_msg(msg) -> None:
        if msg.type in ("error", "warning"):
            log(f"CONSOLE {msg.type.upper()}: {msg.text[:300]}")

    page.on("console", on_msg)
    page.on("pageerror", lambda exc: log(f"PAGE ERROR: {str(exc)[:300]}"))


async def count_status_messages(page: Page) -> dict:
    """Read chat message count and count of 'Execution status:' bubbles from the DOM."""
    return await page.evaluate(
        """
        () => {
            const bubbles = document.querySelectorAll(
                'div.max-w-\\\\[92\\\\%\\\\].rounded-xl'
            );
            const total = bubbles.length;
            let statusCount = 0;
            const statusTexts = new Set();
            bubbles.forEach((b) => {
                const t = (b.textContent || '').trim();
                if (t.startsWith('Execution status:')) {
                    statusCount += 1;
                    statusTexts.add(t);
                }
            });
            // Also check the visible message count text if present
            const countLabel = Array.from(document.querySelectorAll('*'))
                .map(n => n.textContent || '')
                .find(t => /\\d+\\s*messages?/.test(t));
            return {
                total,
                statusCount,
                statusTexts: Array.from(statusTexts),
                visibleCountLabel: countLabel ? countLabel.slice(0, 80) : null,
            };
        }
        """
    )


async def main() -> int:
    log("=== Fix B regression check ===")
    log(f"Evidence dir: {EVIDENCE}")

    report: dict = {
        "started": time.time(),
        "checkpoints": [],
        "errors": [],
        "verdict": "UNKNOWN",
    }

    # Unique creds so this run is independent
    suffix = uuid.uuid4().hex[:8]
    email = f"fixbcheck_{suffix}@example.com"
    password = "TestPass!2026"
    test_name = f"FixB-regression-{suffix}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=r"C:\Users\midhu\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe",
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        await attach_console(page)

        # 1. Signup
        log("1) Signup")
        await page.goto(f"{FRONTEND}/signup", wait_until="domcontentloaded")
        await page.wait_for_selector("input[placeholder='Full name']", timeout=10000)
        await page.fill("input[placeholder='Full name']", "Fix B Checker")
        await page.fill("input[placeholder='Email']", email)
        await page.fill("input[placeholder='Password']", password)
        await page.locator("button:has-text('Create account')").click()
        await page.wait_for_url(f"{FRONTEND}/dashboard", timeout=15000)
        log("   signed up, on dashboard")

        # 2. Open run-test page and wait for it to be ready
        log("2) Open /run-test")
        await page.goto(f"{FRONTEND}/run-test", wait_until="networkidle")
        await page.wait_for_selector("input[placeholder='Enter target URL']", timeout=10000)

        # 3. Fill the form
        log("3) Fill form")
        await page.fill("input[placeholder='Enter target URL']", "https://www.saucedemo.com")
        await page.fill("input[placeholder='Enter test name...']", test_name)
        # Goal: type into the AI Copilot textarea
        textarea = page.locator("textarea").first
        await textarea.fill("log in as standard_user, add one item to the cart, then verify the cart badge shows 1")
        await page.wait_for_timeout(500)

        # CHECKPOINT 0: before submission
        log("CHECKPOINT 0: idle (before test starts)")
        await page.wait_for_timeout(1000)
        c0 = await count_status_messages(page)
        log(f"   total bubbles={c0['total']}  status bubbles={c0['statusCount']}  label={c0['visibleCountLabel']}")
        report["checkpoints"].append({"label": "idle_before_submit", **c0})

        # 4. Install route interception to inject ai_plan into /api/tests/start
        log("4) Install /api/tests/start route interception")
        await page.route(
            "**/api/tests/start",
            lambda route, _req: route.continue_(
                post_data=json.dumps(
                    {
                        "url": "https://www.saucedemo.com",
                        "testName": test_name,
                        "goal": "log in as standard_user, add one item to the cart, then verify the cart badge shows 1",
                        "testType": "e2e",
                        "browser": "chromium",
                        "aiPlan": {
                            "summary": "FixB regression probe",
                            "page_title": "Sauce Demo",
                            "instruction": "log in as standard_user, add one item to the cart, then verify the cart badge shows 1",
                            "test_case": {
                                "name": "FixB probe",
                                "description": "Adds one item to cart and checks badge",
                                "steps": [
                                    {"action": "navigate", "target": "https://www.saucedemo.com"},
                                    {"action": "type", "selector": "#user-name", "value": "standard_user"},
                                    {"action": "type", "selector": "#password", "value": "secret_sauce"},
                                    {"action": "click", "selector": "#login-button"},
                                    {"action": "click", "selector": ".inventory_item button"},
                                    {"action": "assert_text", "selector": ".shopping_cart_badge", "value": "1"},
                                ],
                            },
                        },
                    }
                )
            ),
        )

        # 5. Click Run Test
        log("5) Click Run Test")
        await page.locator("button:has-text('Run Test')").click()

        # Wait until the AI Copilot chat shows at least one "Execution status: running"
        log("6) Wait for Execution status: running to appear")
        try:
            await page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll(
                    'div.max-w-\\\\[92\\\\%\\\\].rounded-xl'
                )).some(b => (b.textContent || '').trim().startsWith('Execution status: running'))
                """,
                timeout=60000,
            )
            log("   'Execution status: running' appeared")
        except PWTimeout:
            log("   TIMEOUT waiting for running status")

        # Let several polls happen to give the regression a chance to manifest
        log("7) Sleep 15s to accumulate any duplicate-status messages")
        await page.wait_for_timeout(15000)

        c1 = await count_status_messages(page)
        log(
            f"   CHECKPOINT 1 (running, 15s after first status): total={c1['total']}  "
            f"status={c1['statusCount']}  distinct_status_texts={len(c1['statusTexts'])}"
        )
        log(f"   distinct status texts: {c1['statusTexts']}")
        report["checkpoints"].append({"label": "running_15s", **c1})
        await page.screenshot(path=str(EVIDENCE / "01_running_15s.png"), full_page=False)

        log("8) Sleep another 30s (45s total running)")
        await page.wait_for_timeout(30000)
        c2 = await count_status_messages(page)
        log(
            f"   CHECKPOINT 2 (running, 45s after first status): total={c2['total']}  "
            f"status={c2['statusCount']}  distinct_status_texts={len(c2['statusTexts'])}"
        )
        log(f"   distinct status texts: {c2['statusTexts']}")
        report["checkpoints"].append({"label": "running_45s", **c2})
        await page.screenshot(path=str(EVIDENCE / "02_running_45s.png"), full_page=False)

        # Wait for terminal status
        log("9) Wait for Execution status: completed* (terminal)")
        try:
            await page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll(
                    'div.max-w-\\\\[92\\\\%\\\\].rounded-xl'
                )).some(b => {
                    const t = (b.textContent || '').trim();
                    return t.startsWith('Execution status: completed') ||
                           t.startsWith('Execution status: failed') ||
                           t.startsWith('Execution status: timed_out');
                })
                """,
                timeout=300000,
            )
            log("   terminal status appeared")
        except PWTimeout:
            log("   TIMEOUT waiting for terminal status")

        c3 = await count_status_messages(page)
        log(
            f"   CHECKPOINT 3 (terminal): total={c3['total']}  "
            f"status={c3['statusCount']}  distinct_status_texts={len(c3['statusTexts'])}"
        )
        log(f"   distinct status texts: {c3['statusTexts']}")
        report["checkpoints"].append({"label": "terminal", **c3})
        await page.screenshot(path=str(EVIDENCE / "03_terminal.png"), full_page=False)

        await context.close()
        await browser.close()

    # Verdict
    final_status = c3["statusCount"] if "c3" in dir() else -1
    if final_status <= 2 and final_status >= 0:
        verdict = "PASS: at most 2 'Execution status:' bubbles (1 running + 1 terminal)"
    elif final_status <= 5:
        verdict = f"WARN: {final_status} status bubbles (expected ≤ 2)"
    else:
        verdict = f"FAIL: {final_status} status bubbles (regression NOT fixed)"

    report["verdict"] = verdict
    report["finished"] = time.time()
    LOG_PATH.write_text("\n".join(console_lines), encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    log(f"VERDICT: {verdict}")
    log(f"Report: {REPORT_PATH}")
    log(f"Console: {LOG_PATH}")
    return 0 if "PASS" in verdict or "WARN" in verdict else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
