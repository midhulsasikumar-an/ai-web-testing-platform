def test_title(page):
    try:
        title = page.title()

        if title:
            return {"test": "Check Title", "status": "pass", "details": title}
        else:
            return {"test": "Check Title", "status": "fail", "error": "Title is empty"}

    except Exception as e:
        return {"test": "Check Title", "status": "fail", "error": str(e)}