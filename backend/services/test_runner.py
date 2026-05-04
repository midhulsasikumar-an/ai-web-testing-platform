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

def run_test(url: str, test_id: str):
    results = []
    screenshot_path = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=30000, wait_until="domcontentloaded")

        # ---- STEP 1: Initial viewport ----
        test_result, screenshot_path = test_page_load( test_id, page)
        results.append(test_result)

        results.append(test_title(page))

        # ---- Check for error page before proceeding ----
        error_result = test_error_page(page)
        results.append(error_result)

        if error_result["status"] == "fail":
            return results, screenshot_path

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
        results.append(test_buttons(page))
        results.append(test_console_errors(page))
        results.append(test_content(page))
        results.append(test_performance(page))

        browser.close()

    return results, screenshot_path