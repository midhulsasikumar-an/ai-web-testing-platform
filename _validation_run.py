"""Real Playwright UI validation of Fix A and Fix B against a fresh Saucedemo run.

Captures:
  - Screenshot of Run Test page while status=running
  - Screenshot of Run Test page after status=terminal
  - Text of AI Copilot chat at both states (Fix B)
  - Text of terminal log rows at both states (Fix A)
  - Screenshot of Test History after completion
  - API response of the test from the backend
"""

import os
import sys
import time
import uuid
import json
import re
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "http://127.0.0.1:3000"
API = "http://127.0.0.1:8001"
SCREENSHOT_DIR = Path("C:/Internship/ai-testing-platform/_validation")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

EMAIL = f"playwright_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "Test1234!"
NAME = "Playwright Phase2"


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    log(f"Creating screenshots in {SCREENSHOT_DIR}")
    log(f"Test user: {EMAIL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        page.set_default_timeout(15000)

        # -------- 1. Sign up --------
        log("1. Sign up")
        page.goto(f"{BASE}/signup", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.fill('input[placeholder="Full name"]', NAME)
        page.fill('input[placeholder="Email"]', EMAIL)
        page.fill('input[placeholder="Password"]', PASSWORD)
        page.screenshot(path=str(SCREENSHOT_DIR / "01_signup_filled.png"), full_page=True)
        with page.expect_navigation(timeout=20000):
            page.click('button[type="submit"]')
        log(f"   After signup URL: {page.url}")

        # -------- 2. Navigate to Run Test --------
        log("2. Navigate to /run-test")
        page.goto(f"{BASE}/run-test", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.screenshot(path=str(SCREENSHOT_DIR / "02_run_test_initial.png"), full_page=True)

        # Pre-generate an AI plan via API (so we can inject ai_plan into the form submission
        # to force the AI plan path; the legacy path has a pre-existing import bug).
        import requests as _req
        # Read auth token that the frontend already stored in localStorage after signup
        auth_token_ls = page.evaluate("() => window.localStorage.getItem('auth_token')")
        log(f"   auth_token from localStorage: {(auth_token_ls or '')[:20]}...")
        api_H = {"Authorization": f"Bearer {auth_token_ls}"}
        plan_r = _req.post(
            f"{API}/ai/plan",
            headers=api_H,
            json={
                "url": "https://www.saucedemo.com",
                "instruction": "Test login with standard_user and secret_sauce, add an item to the cart, verify it appears",
                "test_type": "ai",
            },
            timeout=90,
        )
        log(f"   POST /ai/plan -> {plan_r.status_code}")
        plan = plan_r.json()
        log(f"   plan steps: {len((plan or {}).get('test_case', {}).get('steps', []))}")

        # Set up request interception: when the page POSTs /api/tests/start, inject ai_plan
        def handle_route(route):
            if route.request.method == "POST" and "/api/tests/start" in route.request.url:
                try:
                    body = json.loads(route.request.post_data or "{}")
                except Exception:
                    body = {}
                body["ai_plan"] = plan
                body["test_type"] = "ai"
                if "coverage_level" not in body:
                    body["coverage_level"] = "standard"
                log(f"   INTERCEPTED POST /api/tests/start -> injecting ai_plan (test_name={body.get('test_name')!r})")
                route.continue_(
                    headers={**route.request.headers, "content-type": "application/json"},
                    post_data=json.dumps(body),
                )
            else:
                route.continue_()
        page.route("**/*", handle_route)

        # -------- 3. Fill form --------
        log("3. Fill Run Test form")
        url_input = page.locator('input[placeholder="Enter target URL"]').first
        url_input.fill("https://www.saucedemo.com")
        name_input = page.locator('input[placeholder="Enter test name..."]').first
        name_input.fill(f"Playwright Phase2 {uuid.uuid4().hex[:6]}")
        goal_textarea = page.locator('textarea').first
        goal_textarea.fill("Test login with standard_user and secret_sauce, add an item to the cart, verify it appears")
        page.screenshot(path=str(SCREENSHOT_DIR / "03_run_test_filled.png"), full_page=True)

        # -------- 4. Click Run Test --------
        log("4. Click Run Test button")
        run_button = page.locator('button:has-text("Run Test")').first
        with page.expect_response(lambda r: "/api/tests/start" in r.url and r.request.method == "POST", timeout=30000) as start_resp_info:
            run_button.click()
        start_resp = start_resp_info.value
        log(f"   POST /api/tests/start -> {start_resp.status}")
        start_body = start_resp.json()
        test_id = start_body.get("test_id") or (start_body.get("data") or {}).get("test_id")
        log(f"   test_id = {test_id}")

        if not test_id:
            raise RuntimeError(f"Failed to start test: {start_body}")

        # Capture running state quickly (within first 10s)
        log("5. Capture RUNNING state evidence (T+5s)")
        time.sleep(5)
        page.screenshot(path=str(SCREENSHOT_DIR / "04_run_test_running.png"), full_page=True)

        # Use targeted DOM queries for the AI Copilot messages and the Terminal log rows.
        # The AIChatPanel renders messages as divs with class containing rounded-xl and max-w-[92%].
        # The terminal renders log rows with class containing border-slate-800/80 and bg-slate-950/80.
        # The Run Test page's status pill is in the summary card.

        def collect_chat_messages(p):
            # Use page.evaluate to find the messages via JS DOM walking.
            # The AIChatPanel renders message bubbles as <div class="... max-w-[92%] rounded-xl ..."> {msg.text} </div>
            # We look for divs whose text starts with "Execution status:" or is a known message.
            try:
                result = p.evaluate("""() => {
                    const bubbles = [];
                    const all = document.querySelectorAll('div.max-w-\\\\[92\\\\%\\\\].rounded-xl');
                    for (const el of all) {
                        const t = (el.textContent || '').trim();
                        // Only include chat messages (text-only, short)
                        if (t && t.length < 500 && (t.startsWith('Execution status:') || t.startsWith('AI:') || t.startsWith('Detected') || t.startsWith('Created') || t.startsWith('Ask') || t.startsWith('Hi'))) {
                            bubbles.push(t);
                        }
                    }
                    return bubbles;
                }""")
                return result
            except Exception as e:
                log(f"   collect_chat_messages error: {e}")
                return []

        def collect_terminal_rows(p):
            # Find the terminal section by the h2 text, then look at log rows inside.
            # The terminal has a section containing "Execution Terminal" h2.
            # Each row is a div with class containing border-slate-800/80 and bg-slate-950/80.
            rows = p.locator("div.border-slate-800\\/80.bg-slate-950\\/80").all_text_contents()
            return [r.strip() for r in rows if r.strip()]

        def collect_status_pill(p):
            # Status pill: small rounded-full span in headers
            pills = p.locator("span.rounded-full").all_text_contents()
            return [s.strip() for s in pills if s.strip()]

        def collect_summary_status(p):
            # The top summary card status — text near the top of the page after "completed" or "Test"
            try:
                t = p.locator("body").inner_text(timeout=5000)
                # Look for first "completed" or "failed" etc near the top
                m = re.search(r"\b(completed|completed_with_failures|failed|timed_out|cancelled|passed|running)\b", t, re.IGNORECASE)
                return m.group(0) if m else "NOT_FOUND"
            except Exception:
                return "NOT_FOUND"

        chat_msgs_running = collect_chat_messages(page)
        terminal_rows_running = collect_terminal_rows(page)
        status_pills_running = collect_status_pill(page)
        summary_status_running = collect_summary_status(page)

        log(f"   AI Copilot messages (running): {len(chat_msgs_running)} bubbles")
        for m in chat_msgs_running:
            log(f"     - {m[:120]!r}")
        log(f"   Status pills (running): {status_pills_running}")
        log(f"   Summary status text (running): {summary_status_running!r}")
        log(f"   Terminal rows (running): {len(terminal_rows_running)}")
        # Show first 3 + last 3
        for r in terminal_rows_running[:3]:
            log(f"     first - {r[:120]!r}")
        for r in terminal_rows_running[-3:]:
            log(f"     last  - {r[:120]!r}")

        # Verify "Execution status: running" is in the chat
        ai_status_running = "NOT_FOUND"
        for m in chat_msgs_running:
            mm = re.search(r"Execution status: \w+", m)
            if mm:
                ai_status_running = mm.group(0)
                break
        log(f"   AI status (running) = {ai_status_running!r}")

        # Count blank rows in terminal: a row that contains only [time] and INFO/level with no other text
        blank_rows_running = [r for r in terminal_rows_running if re.match(r"^\[\d{1,2}:\d{2}:\d{2}\]\s+\w+\s*$", r)]
        log(f"   Terminal blank rows (running): {len(blank_rows_running)} / {len(terminal_rows_running)} total rows")

        # Save raw text for the report
        (SCREENSHOT_DIR / "05_chat_running.txt").write_text("\n".join(chat_msgs_running), encoding="utf-8")
        (SCREENSHOT_DIR / "05_terminal_running.txt").write_text("\n".join(terminal_rows_running), encoding="utf-8")
        (SCREENSHOT_DIR / "05_status_pills_running.txt").write_text("\n".join(status_pills_running), encoding="utf-8")

        # -------- 6. Poll API until terminal --------
        log("6. Poll API until terminal")
        import requests
        poll_url = f"{API}/api/tests/{test_id}"
        # Get a token for the test user
        login = requests.post(f"{API}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
        token = login.json().get("access_token") or login.json().get("data", {}).get("access_token")
        H = {"Authorization": f"Bearer {token}"}

        poll_start = time.time()
        last_status = None
        last_log_count = 0
        while time.time() - poll_start < 900:  # 15 min cap
            try:
                r = requests.get(poll_url, headers=H, timeout=10)
                d = r.json()
                status = d.get("status")
                sl = d.get("stream_logs") or []
                if status != last_status or len(sl) - last_log_count >= 100:
                    log(f"   T+{int(time.time()-poll_start):>3}s status={status} logs={len(sl)}")
                    last_status = status
                    last_log_count = len(sl)
                if status in ("completed", "completed_with_failures", "failed", "timed_out", "cancelled"):
                    break
            except Exception as e:
                log(f"   poll error: {e}")
            time.sleep(3)
        else:
            log("   POLL TIMEOUT (15 min)")

        elapsed = int(time.time() - poll_start)
        log(f"   Terminal reached at T+{elapsed}s, status={status}")

        # Get final API state
        final = requests.get(poll_url, headers=H, timeout=10).json()
        sl = final.get("stream_logs") or []
        empty_count = sum(1 for e in sl if not (e.get("msg") or "").strip())
        log(f"   Final stream_logs count: {len(sl)}")
        log(f"   Final empty msg count: {empty_count}")
        (SCREENSHOT_DIR / "06_api_final.json").write_text(
            json.dumps({
                "test_id": test_id,
                "status": final.get("status"),
                "failure_reason": final.get("failure_reason"),
                "updated_at": final.get("updated_at"),
                "stream_logs_count": len(sl),
                "empty_msg_count": empty_count,
                "summary": final.get("summary"),
            }, default=str, indent=2),
            encoding="utf-8",
        )

        # Last 20 stream_logs
        last_20 = sl[-20:]
        (SCREENSHOT_DIR / "07_last_20_stream_logs.json").write_text(
            json.dumps(last_20, default=str, indent=2), encoding="utf-8"
        )
        log("   Last 10 terminal log lines (msg field):")
        for e in sl[-10:]:
            log(f"     [{(e.get('type') or '?')[:20]:<20}] {(e.get('msg') or '')[:80]}")

        # Give the frontend polling loop time to catch up (it polls every 2s)
        log("7. Wait for frontend to catch up (3s)")
        time.sleep(3)

        # -------- 7. Capture post-terminal UI evidence --------
        log("8. Capture post-terminal evidence")
        # Force the page to re-fetch the test (a manual reload ensures the latest state)
        # but the existing polling should already have caught it. Just screenshot.
        try:
            page.wait_for_function(
                "() => !document.body.innerText.includes('Running…') && !document.body.innerText.includes('Running...')",
                timeout=15000,
            )
            log("   Frontend exited Running state")
        except PWTimeout:
            log("   WARNING: Frontend still in Running state after 15s")

        page.screenshot(path=str(SCREENSHOT_DIR / "08_run_test_terminal.png"), full_page=True)

        chat_msgs_terminal = collect_chat_messages(page)
        terminal_rows_terminal = collect_terminal_rows(page)
        status_pills_terminal = collect_status_pill(page)
        summary_status_terminal = collect_summary_status(page)

        log(f"   AI Copilot messages (terminal): {len(chat_msgs_terminal)} bubbles")
        for m in chat_msgs_terminal:
            log(f"     - {m[:120]!r}")
        log(f"   Status pills (terminal): {status_pills_terminal}")
        log(f"   Summary status text (terminal): {summary_status_terminal!r}")
        log(f"   Terminal rows (terminal): {len(terminal_rows_terminal)}")

        ai_status_terminal = "NOT_FOUND"
        for m in chat_msgs_terminal:
            mm = re.search(r"Execution status: \w+", m)
            if mm:
                ai_status_terminal = mm.group(0)
                break
        log(f"   AI status (terminal) = {ai_status_terminal!r}")

        (SCREENSHOT_DIR / "09_chat_terminal.txt").write_text("\n".join(chat_msgs_terminal), encoding="utf-8")
        (SCREENSHOT_DIR / "09_terminal_terminal.txt").write_text("\n".join(terminal_rows_terminal), encoding="utf-8")
        (SCREENSHOT_DIR / "09_status_pills_terminal.txt").write_text("\n".join(status_pills_terminal), encoding="utf-8")

        (SCREENSHOT_DIR / "09_chat_terminal.txt").write_text(chat_terminal, encoding="utf-8")
        (SCREENSHOT_DIR / "09_terminal_terminal.txt").write_text(terminal_terminal, encoding="utf-8")

        # Check Run button state (should NOT be "Running...")
        try:
            run_btn_text = page.locator('button:has-text("Run Test"), button:has-text("Running")').first.inner_text(timeout=5000)
            log(f"   Run button text: {run_btn_text!r}")
        except PWTimeout:
            run_btn_text = "BUTTON_NOT_FOUND"
            log(f"   Run button text: {run_btn_text!r}")
        # Check whether the button is disabled (frontend behaviour after terminal)
        try:
            run_btn_disabled = page.locator('button:has-text("Run Test"), button:has-text("Running")').first.is_disabled()
            log(f"   Run button disabled: {run_btn_disabled}")
        except Exception:
            run_btn_disabled = None

        # -------- 9. Navigate to Test History --------
        log("9. Navigate to /test-history")
        page.goto(f"{BASE}/test-history", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOT_DIR / "10_test_history.png"), full_page=True)
        history_text = page.locator("main").inner_text(timeout=5000) if page.locator("main").count() > 0 else page.locator("body").inner_text(timeout=5000)
        log(f"   Test History page snippet: {history_text[:600]!r}")
        history_has_our_test = False
        if test_id and test_id[:8] in history_text:
            history_has_our_test = True
            log(f"   ✓ Test ID {test_id[:8]}... visible on /test-history")
        elif "Playwright Phase2" in history_text:
            history_has_our_test = True
            log(f"   ✓ 'Playwright Phase2' visible on /test-history")
        else:
            log(f"   (neither test_id prefix nor 'Playwright Phase2' found in history text)")
        # Try to click into the row's detail
        try:
            link = page.locator("text=Playwright Phase2").first
            if link.count() > 0:
                link.click(timeout=5000)
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1)
                page.screenshot(path=str(SCREENSHOT_DIR / "11_test_detail.png"), full_page=True)
                log(f"   Test detail URL: {page.url}")
        except Exception as e:
            log(f"   Could not click into test detail: {e}")

        # -------- 10. Save final report --------
        log("10. Save final report")
        report = {
            "test_id": test_id,
            "user_email": EMAIL,
            "polling_elapsed_s": elapsed,
            "api_final_status": final.get("status"),
            "api_final_failure_reason": final.get("failure_reason"),
            "api_final_stream_logs_count": len(sl),
            "api_final_empty_msg_count": empty_count,
            "ai_status_running": ai_status_running,
            "ai_status_terminal": ai_status_terminal,
            "ai_status_changed": ai_status_running != ai_status_terminal and ai_status_running != "NOT_FOUND" and ai_status_terminal != "NOT_FOUND",
            "ai_messages_count_running": len(chat_msgs_running),
            "ai_messages_count_terminal": len(chat_msgs_terminal),
            "ai_messages_terminal_full": chat_msgs_terminal,
            "ai_messages_running_full": chat_msgs_running,
            "status_pills_running": status_pills_running,
            "status_pills_terminal": status_pills_terminal,
            "summary_status_running": summary_status_running,
            "summary_status_terminal": summary_status_terminal,
            "terminal_rows_count_running": len(terminal_rows_running),
            "terminal_rows_count_terminal": len(terminal_rows_terminal),
            "terminal_blank_rows_running": len(blank_rows_running),
            "run_button_text_post_terminal": run_btn_text,
            "run_button_disabled_post_terminal": run_btn_disabled,
            "frontend_exited_running": "Running…" not in run_btn_text and "Running..." not in run_btn_text,
            "test_id_visible_in_history": history_has_our_test,
            "evidence_files": sorted(p.name for p in SCREENSHOT_DIR.glob("*")),
        }
        (SCREENSHOT_DIR / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        log("===== REPORT =====")
        log(json.dumps(report, indent=2))

        ctx.close()
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
