import os

def test_page_load(test_id: str, page):
    try:
        page.wait_for_timeout(3000) #small buffer to ensure all resources are loaded

        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = f"screenshots/{test_id}.png"
        page.screenshot(path=screenshot_path)

        return {"test": "Page Load", "status": "pass"}, screenshot_path

    except Exception as e:
        return {"test": "Page Load", "status": "fail", "error": str(e)}, None