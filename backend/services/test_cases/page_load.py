import os

def test_page_load(page, folder_path, test_id: str,screenshots):
    try:
        page.wait_for_timeout(3000) #small buffer to ensure all resources are loaded

        home_path = f"{folder_path}/home.png"

        page.screenshot(path=home_path)

        screenshots["home"] = f"/screenshots/{test_id}/home.png"

        return {"test": "Page Load", "status": "pass"}

    except Exception as e:
        return {"test": "Page Load", "status": "fail", "error": str(e)}, None