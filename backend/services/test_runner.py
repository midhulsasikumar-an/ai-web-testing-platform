import os
import json
import asyncio
from datetime import datetime
from playwright.sync_api import sync_playwright
from backend.services.test_cases.error_page_test import test_error_page
from backend.services.test_cases.page_load import test_page_load
from backend.services.test_cases.title_check import test_title  
from backend.services.test_cases.UI_check import test_critical_elements
from backend.services.test_cases.interactions_test import test_links   
from backend.services.test_cases.input_test import test_input_fields
from backend.services.test_cases.button_test import test_buttons
from backend.services.test_cases.console_test import test_console_errors
from backend.services.test_cases.content_check import test_content
from backend.services.test_cases.performance_check import test_performance
from backend.models.schema import TestRequest
from backend.agent.services.website_health_service import WebsiteHealthService
from backend.agent.services.form_fuzzing_service import FormFuzzingService
from backend.database.mongo import db

def run_test(url: str, test_id: str, user_id: str | None = None):
    results = []
    screenshots = []
    artifacts = {
        "execution_id": test_id,
        "user_id": user_id,
        "screenshots": [],
        "console_logs": [],
        "network_logs": [],
        "dom_snapshots": [],
        "cookies": [],
        "metadata": {"url": url},
        "form_fuzzing": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Collect console and network logs
        def _on_console(msg):
            artifacts["console_logs"].append({"type": msg.type, "text": msg.text})

        def _on_request(req):
            artifacts["network_logs"].append({"url": req.url, "method": req.method, "resource_type": req.resource_type})

        def _on_response(resp):
            try:
                artifacts["network_logs"].append({"url": resp.url, "status": resp.status, "ok": resp.ok})
            except Exception:
                artifacts["network_logs"].append({"url": resp.url})

        page.on("console", _on_console)
        page.on("request", _on_request)
        page.on("response", _on_response)

        page.goto(url, timeout=30000, wait_until="domcontentloaded")

        folder_path = f"artifacts/{test_id}"
        os.makedirs(folder_path, exist_ok=True)
        # ---- STEP 1: Initial viewport ----
        # capture initial DOM and screenshot
        try:
            dom = page.content()
            artifacts["dom_snapshots"].append(dom)
        except Exception:
            pass

        initial_shot = f"{folder_path}/initial.png"
        try:
            page.screenshot(path=initial_shot, full_page=True)
            artifacts["screenshots"].append(initial_shot)
        except Exception:
            pass

        results.append(test_page_load(page, folder_path, test_id, artifacts))

        results.append(test_title(page))

        # ---- Check for error page before proceeding ----
        error_result = test_error_page(page, folder_path, test_id, screenshots)
        results.append(error_result)

        if error_result["status"] == "fail":
            return results, screenshots

        # ---- STEP 2: Scroll in stages ----
        for i in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1000)

            {
                "test": "Scroll Coverage",
                "status": "info",
                "details": "Page scrolled (3 steps)"
            }

        # ---- STEP 3: Run tests after scroll ----
        results.append(test_critical_elements(page))
        results.append(test_links(page))
        results.append(test_input_fields(page))
        results.append(test_buttons(page, folder_path, test_id, artifacts))
        results.append(test_console_errors(page))
        results.append(test_content(page))
        results.append(test_performance(page))

        # --- FORM FUZZING ---
        try:
            fuzz = FormFuzzingService()
            fuzz_res = fuzz.fuzz_forms(page, folder_path, test_id)
            artifacts["form_fuzzing"] = fuzz_res
            results.append({"test": "form_fuzzing", "status": "info", "details": f"{len(fuzz_res)} trials"})
        except Exception as e:
            results.append({"test": "form_fuzzing", "status": "error", "error": str(e)})

        # collect cookies
        try:
            artifacts["cookies"] = [c for c in page.context.cookies()]
        except Exception:
            artifacts["cookies"] = []

        # final DOM snapshot
        try:
            artifacts["dom_snapshots"].append(page.content())
        except Exception:
            pass

        browser.close()

    # Run QA analyzers (WebsiteHealthService is async)
    try:
        health_service = WebsiteHealthService()
        health_report = asyncio.run(health_service.analyze(artifacts))
    except Exception as e:
        health_report = {"error": str(e)}

    # attach health report to results
    results.append({"test": "website_health_analysis", "status": "completed", "details": health_report})

    # persist artifacts metadata
    meta_path = f"{folder_path}/artifacts.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(artifacts, fh, default=str, indent=2)
        db["artifacts"].update_one(
            {"execution_id": test_id, "user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "execution_id": test_id,
                "artifact_path": meta_path,
                "screenshot_paths": list(artifacts.get("screenshots", [])),
                "created_at": datetime.utcnow().isoformat(),
            }},
            upsert=True,
        )
    except Exception:
        pass

    return results, artifacts