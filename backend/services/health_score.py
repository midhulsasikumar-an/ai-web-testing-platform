def calculate_health_score(results):
    if not results:
        return {
            "score": 0,
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "info": 0
            }
        }
    score = 0
    total = len(results) * 10

    for r in results:
        if r["status"] == "pass":
            score += 10
        elif r["status"] == "info":
            score += 5

    percentage = int((score / total) * 100)

    return {
        "score": percentage,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "failed": sum(1 for r in results if r["status"] == "fail"),
            "info": sum(1 for r in results if r["status"] == "info")
        }
    }
