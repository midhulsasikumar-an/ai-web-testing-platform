def test_performance(page):
    try:
        load_time = page.evaluate("""
            () => {
                const timing = performance.timing;
                return timing.loadEventEnd - timing.navigationStart;
            }
        """)

        # Sometimes value can be 0 if not ready
        if not load_time or load_time < 0:
            return {
                "test": "Performance Check",
                "status": "info",
                "details": "Performance timing not available"
            }

        if load_time > 5000:
            return {
                "test": "Performance Check",
                "status": "fail",
                "details": f"Slow load time: {load_time} ms"
            }

        if load_time > 3000:
            return {
                "test": "Performance Check",
                "status": "info",
                "details": f"Moderate load time: {load_time} ms"
            }

        return {
            "test": "Performance Check",
            "status": "pass",
            "details": f"Fast load time: {load_time} ms"
        }

    except Exception as e:
        return {
            "test": "Performance Check",
            "status": "fail",
            "error": str(e)
        }