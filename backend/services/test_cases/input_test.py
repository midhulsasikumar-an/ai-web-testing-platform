def test_input_fields(page):
    try:
        inputs = page.query_selector_all(
            "input, textarea, [contenteditable='true']"
        )

        visible_inputs = []

        for field in inputs:
            try:
                if field.is_visible():
                    visible_inputs.append(field)
            except:
                continue

        count = len(visible_inputs)

        if count == 0:
            return {
                "test": "Input Fields",
                "status": "info",
                "details": "No input fields present"
            }

        return {
            "test": "Input Fields",
            "status": "pass",
            "details": f"{count} inputs found"
        }

    except Exception as e:
        return {
            "test": "Input Fields",
            "status": "fail",
            "error": str(e)
        }
