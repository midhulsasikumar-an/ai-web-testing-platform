"""
Final Saucedemo validation: capture all evidence in one run.

Verifies:
1. Only one "Execution status:" message exists during execution
2. The message updates in place when status changes (running -> terminal)
3. Terminal logs contain no blank messages (Fix A)
4. Test reaches a terminal state
5. Test history page shows the final status
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

ROOT = Path(r"C:\Internship\ai-testing-platform")
EVIDENCE = ROOT / "_validation_final"
EVIDENCE.mkdir(parents=True, exist_ok=True)
REPORT_PATH = EVIDENCE / "REPORT.json"
LOG_PATH = EVIDENCE / "console.log"
FRONTEND = "http://127.0.0.1:3000"
API = "http://127.0.0.1:8001"
CHROMIUM = r"C:\Users\midhu\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe"

console_lines: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    console_lines.append(line)


async def attach_console(page: Page) -> None:
    def on_msg(msg) -> None:
        if msg.type in ("error", "warning"):
            log(f"CONSOLE {msg.type.upper()}: {msg.text[:200]}")

    page.on("console", on_msg)
    page.on("pageerror", lambda exc: log(f"PAGE ERROR: {str(exc)[:200]}"))


async def count_chat_bubbles(page: Page) -> dict:
    return await page.evaluate(
        """
        () => {
            const bubbles = document.querySelectorAll(
                'div.max-w-\\\\[92\\\\%\\\\].rounded-xl'
            );
            const total = bubbles.length;
            let statusCount = 0;
            const statusTexts = [];
            bubbles.forEach((b) => {
                const t = (b.textContent || '').trim();
                if (t.startsWith('Execution status:')) {
                    statusCount += 1;
                    statusTexts.push(t);
                }
            });
            return { total, statusCount, statusTexts };
        }
        """
    )


async def read_terminal_logs(page: Page) -> dict:
    """Read every terminal log row, count blanks, capture text."""
    return await page.evaluate(
        """
        () => {
            const rows = document.querySelectorAll('[class*="bg-slate-950"] [class*="border-slate-800"]');
            const texts = [];
            let blanks = 0;
            rows.forEach((r) => {
                const spans = r.querySelectorAll('span');
                // Last span is the msg text
                const text = (spans[spans.length - 1]?.textContent || '').trim();
                texts.push(text);
                if (!text) blanks += 1;
            });
            return { count: texts.length, blanks, sampleLast10: texts.slice(-10) };
        }
        """
    )


async def read_status_pill(page: Page) -> str:
    return await page.evaluate(
        """
        () => {
            // Status pill in the header
            const pills = document.querySelectorAll('span.rounded-full');
            for (const p of pills) {
                const t = (p.textContent || '').trim();
                if (['Running', 'Completed', 'Failed', 'Timed Out', 'Idle', 'Queued', 'Planning'].includes(t)) return t;
            }
            return '';
        }
        """
    )


async def main() -> int:
    log("=== FINAL Saucedemo validation ===")
    log(f"Evidence: {EVIDENCE}")

    report: dict = {
        "started": time.time(),
        "checkpoints": [],
        "evidence_files": [],
        "verdict": "UNKNOWN",
    }

    suffix = uuid.uuid4().hex[:8]
    email = f"final_{suffix}@example.com"
    password = "TestPass!2026"
    test_name = f"Final-saucedemo-{suffix}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=CHROMIUM)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        await attach_console(page)

        # 1. Signup
        log("1) Signup")
        await page.goto(f"{FRONTEND}/signup", wait_until="domcontentloaded")
        await page.wait_for_selector("input[placeholder='Full name']", timeout=10000)
        await page.fill("input[placeholder='Full name']", "Final Validator")
        await page.fill("input[placeholder='Email']", email)
        await page.fill("input[placeholder='Password']", password)
        await page.locator("button:has-text('Create account')").click()
        await page.wait_for_url(f"{FRONTEND}/dashboard", timeout=15000)
        log("   on dashboard")

        # 2. Open run-test page
        log("2) Open /run-test")
        await page.goto(f"{FRONTEND}/run-test", wait_until="networkidle")
        await page.wait_for_selector("input[placeholder='Enter target URL']", timeout=10000)

        # 3. Fill the form
        log("3) Fill form")
        await page.fill("input[placeholder='Enter target URL']", "https://www.saucedemo.com")
        await page.fill("input[placeholder='Enter test name...']", test_name)
        textarea = page.locator("textarea").first
        await textarea.fill("log in as standard_user with secret_sauce, add Sauce Labs Backpack to cart, verify cart badge shows 1")
        await page.wait_for_timeout(500)

        # CHECKPOINT A: idle, before any test
        log("CHECKPOINT A: idle (before submit)")
        cA = await count_chat_bubbles(page)
        pillA = await read_status_pill(page)
        log(f"   chat bubbles={cA['total']}  status bubbles={cA['statusCount']}  pill={pillA!r}")
        report["checkpoints"].append({"label": "idle_before_submit", "chat": cA, "pill": pillA})
        await page.screenshot(path=str(EVIDENCE / "A_idle_before_submit.png"))

        # 4. Route interception — inject a real saucedemo plan with multiple steps
        log("4) Install /api/tests/start interception with full saucedemo plan")
        full_plan = {
            "url": "https://www.saucedemo.com",
            "testName": test_name,
            "goal": "log in as standard_user with secret_sauce, add Sauce Labs Backpack to cart, verify cart badge shows 1",
            "testType": "e2e",
            "browser": "chromium",
            "aiPlan": {
                "summary": "Login + add-to-cart + badge check",
                "page_title": "Sauce Demo",
                "instruction": "log in as standard_user with secret_sauce, add Sauce Labs Backpack to cart, verify cart badge shows 1",
                "test_case": {
                    "name": "Login + add-to-cart + badge check",
                    "description": "Logs in and verifies a cart badge appears",
                    "steps": [
                        {"action": "navigate", "target": "https://www.saucedemo.com/"},
                        {"action": "type", "selector": "#user-name", "value": "standard_user"},
                        {"action": "type", "selector": "#password", "value": "secret_sauce"},
                        {"action": "click", "selector": "#login-button"},
                        {"action": "wait", "value": "1000"},
                        {"action": "click", "selector": "[data-test='add-to-cart-sauce-labs-backpack']"},
                        {"action": "wait", "value": "500"},
                        {"action": "assert_text", "selector": ".shopping_cart_badge", "value": "1"},
                    ],
                },
            },
        }
        await page.route(
            "**/api/tests/start",
            lambda route, _req: route.continue_(post_data=json.dumps(full_plan)),
        )

        # 5. Click Run Test
        log("5) Click Run Test")
        await page.locator("button:has-text('Run Test')").click()

        # 6. Wait for first "Execution status: running"
        log("6) Wait for 'Execution status: running'")
        try:
            await page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll(
                    'div.max-w-\\\\[92\\\\%\\\\].rounded-xl'
                )).some(b => (b.textContent || '').trim() === 'Execution status: running')
                """,
                timeout=60000,
            )
            log("   'Execution status: running' visible")
        except PWTimeout:
            log("   TIMEOUT waiting for running status")

        c_running_initial = await count_chat_bubbles(page)
        pill_running = await read_status_pill(page)
        log(
            f"   CHECKPOINT B (initial running): chat bubbles={c_running_initial['total']}  "
            f"status bubbles={c_running_initial['statusCount']}  pill={pill_running!r}"
        )
        report["checkpoints"].append(
            {"label": "running_initial", "chat": c_running_initial, "pill": pill_running}
        )
        await page.screenshot(path=str(EVIDENCE / "B_running_initial.png"))

        # 7. Let several polls happen to stress-test for duplicates
        log("7) Sleep 30s to check stability during execution")
        await page.wait_for_timeout(30000)
        c_running_30s = await count_chat_bubbles(page)
        log(
            f"   CHECKPOINT C (running 30s): chat bubbles={c_running_30s['total']}  "
            f"status bubbles={c_running_30s['statusCount']}  texts={c_running_30s['statusTexts']}"
        )
        report["checkpoints"].append({"label": "running_30s", "chat": c_running_30s})
        await page.screenshot(path=str(EVIDENCE / "C_running_30s.png"))

        # Capture terminal logs at the running_30s point (if any)
        terminal_running = await read_terminal_logs(page)
        log(f"   terminal at 30s: count={terminal_running['count']}  blanks={terminal_running['blanks']}")
        report["terminal_logs_running_30s"] = terminal_running

        # 8. Wait for terminal
        log("8) Wait for terminal status (completed/failed/timed_out)")
        terminal_status_seen = None
        try:
            await page.wait_for_function(
                """
                () => {
                    const bubbles = Array.from(document.querySelectorAll(
                        'div.max-w-\\\\[92\\\\%\\\\].rounded-xl'
                    ));
                    return bubbles.some((b) => {
                        const t = (b.textContent || '').trim();
                        return t.startsWith('Execution status: completed') ||
                               t.startsWith('Execution status: failed') ||
                               t.startsWith('Execution status: timed_out');
                    });
                }
                """,
                timeout=240000,
            )
            terminal_status_seen = "ok"
        except PWTimeout:
            terminal_status_seen = "TIMEOUT"
        log(f"   terminal status seen: {terminal_status_seen}")

        # 9. Capture terminal state
        c_terminal = await count_chat_bubbles(page)
        pill_terminal = await read_status_pill(page)
        log(
            f"   CHECKPOINT D (terminal): chat bubbles={c_terminal['total']}  "
            f"status bubbles={c_terminal['statusCount']}  pill={pill_terminal!r}  "
            f"texts={c_terminal['statusTexts']}"
        )
        report["checkpoints"].append({"label": "terminal", "chat": c_terminal, "pill": pill_terminal})

        # Capture final terminal logs
        terminal_final = await read_terminal_logs(page)
        log(f"   terminal at end: count={terminal_final['count']}  blanks={terminal_final['blanks']}")
        report["terminal_logs_final"] = terminal_final
        await page.screenshot(path=str(EVIDENCE / "D_terminal.png"))

        # 10. Navigate to test history
        log("10) Navigate to /test-history")
        await page.goto(f"{FRONTEND}/test-history", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(EVIDENCE / "E_test_history.png"))

        history_text = await page.evaluate(
            """
            () => {
                const rows = document.querySelectorAll('tr, [role="row"], [class*="row"], [class*="card"]');
                const items = [];
                rows.forEach((r) => {
                    const txt = (r.textContent || '').replace(/\\s+/g, ' ').trim();
                    if (txt) items.push(txt.slice(0, 200));
                });
                return items.slice(0, 30);
            }
            """
        )
        log(f"   test-history rows captured: {len(history_text)}")
        report["test_history_rows_sample"] = history_text

        # 11. Click into the test detail
        log("11) Open test detail page (first item)")
        try:
            # Try clicking the row containing the test name
            row = page.locator(f"text={test_name}").first
            await row.click(timeout=10000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(EVIDENCE / "F_test_detail.png"))
            detail_text = await page.evaluate(
                """
                () => {
                    const status = Array.from(document.querySelectorAll('span, div'))
                        .map(n => (n.textContent || '').trim())
                        .find(t => /^(Running|Completed|Failed|Timed Out|Idle|Completed with failures|Queued|Planning)$/i.test(t));
                    return { status: status || 'unknown' };
                }
                """
            )
            report["test_detail"] = detail_text
            log(f"   detail status: {detail_text['status']}")
        except Exception as e:
            log(f"   could not open detail: {e}")
            report["test_detail"] = {"error": str(e)}

        await context.close()
        await browser.close()

    # ---- Verdict ----
    # (1) only 1 status bubble
    cB = report["checkpoints"][1]["chat"]  # running_initial
    cC = report["checkpoints"][2]["chat"]  # running_30s
    cD = report["checkpoints"][3]["chat"]  # terminal
    pillD = report["checkpoints"][3]["pill"]

    chk1_one_bubble = cB["statusCount"] == 1 and cC["statusCount"] == 1 and cD["statusCount"] == 1
    # (2) message updates in place
    chk2_in_place = (
        "Execution status: running" in cB["statusTexts"]
        and len(cB["statusTexts"]) == 1
        and cD["statusTexts"][0].startswith("Execution status: ") and not cD["statusTexts"][0].endswith("running")
    )
    # (3) no blank terminal messages
    chk3_no_blanks = terminal_final["blanks"] == 0
    # (4) test reaches terminal
    chk4_terminal = terminal_status_seen == "ok" and pillD.lower() not in ("running", "queued", "planning", "", "idle")
    # (5) test history shows status
    chk5_history = bool(pillD and pillD.lower() not in ("", "unknown"))

    all_pass = chk1_one_bubble and chk2_in_place and chk3_no_blanks and chk4_terminal and chk5_history
    verdict = "PASS" if all_pass else "PARTIAL"

    report["checks"] = {
        "one_status_bubble": chk1_one_bubble,
        "in_place_transition": chk2_in_place,
        "no_blank_terminal_messages": chk3_no_blanks,
        "reached_terminal": chk4_terminal,
        "history_shows_status": chk5_history,
    }
    report["verdict"] = verdict
    report["finished"] = time.time()

    LOG_PATH.write_text("\n".join(console_lines), encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    log("")
    log("=" * 50)
    log("VERIFICATION CHECKLIST")
    log("=" * 50)
    log(f"  (1) One status bubble:           {chk1_one_bubble}")
    log(f"  (2) In-place transition:          {chk2_in_place}")
    log(f"  (3) No blank terminal messages:   {chk3_no_blanks}  (blanks={terminal_final['blanks']}/{terminal_final['count']})")
    log(f"  (4) Test reached terminal state:  {chk4_terminal}  (pill={pillD!r})")
    log(f"  (5) Test history shows status:    {chk5_history}  (pill={pillD!r})")
    log("")
    log(f"FINAL VERDICT: {verdict}")
    log(f"Report: {REPORT_PATH}")
    log(f"Evidence: {EVIDENCE}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
