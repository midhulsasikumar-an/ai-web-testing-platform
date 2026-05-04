def test_input_fields(page):
    try:
        inputs = page.query_selector_all("input")

        if not inputs:
            return {
                "test": "Input Fields",
                "status": "info",
                "details": "No input fields present"
            }

        return {
            "test": "Input Fields",
            "status": "pass",
            "details": f"{len(inputs)} inputs found"
        }

    except Exception as e:
        return {"test": "Input Fields", "status": "fail", "error": str(e)}