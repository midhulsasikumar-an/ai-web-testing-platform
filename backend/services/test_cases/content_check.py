def test_content(page):
    try:
        text = page.inner_text("body").strip()

        # Remove extra whitespace
        cleaned_text = " ".join(text.split())

        length = len(cleaned_text)

        if length == 0:
            return {
                "test": "Content Check",
                "status": "fail",
                "error": "No visible content on page"
            }

        if length < 50:
            return {
                "test": "Content Check",
                "status": "info",
                "details": "Low content detected"
            }

        return {
            "test": "Content Check",
            "status": "pass",
            "details": f"Content length: {length} characters"
        }

    except Exception as e:
        return {
            "test": "Content Check",
            "status": "fail",
            "error": str(e)
        }
