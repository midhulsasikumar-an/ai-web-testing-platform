from datetime import datetime


def generate_ai_logs(
    total_tests: int,
    passed: int,
    failed: int,
    warnings: int,
    average_health: int
):
    ai_logs = []

    current_time = datetime.now().strftime("%H:%M:%S")

    if failed > 0:
        ai_logs.append({
            "time": current_time,
            "level": "error",
            "msg": f"{failed} failed test runs detected."
        })

    if warnings > 0:
        ai_logs.append({
            "time": current_time,
            "level": "warn",
            "msg": f"{warnings} warning-level issues found."
        })

    if average_health >= 80:
        ai_logs.append({
            "time": current_time,
            "level": "success",
            "msg": f"System health is stable at {average_health}%."
        })

    elif average_health >= 60:
        ai_logs.append({
            "time": current_time,
            "level": "warn",
            "msg": f"System health dropped to {average_health}%."
        })

    else:
        ai_logs.append({
            "time": current_time,
            "level": "error",
            "msg": f"Critical system health detected: {average_health}%."
        })

    if total_tests > 0:
        ai_logs.append({
            "time": current_time,
            "level": "info",
            "msg": f"{total_tests} total test runs analyzed."
        })

    if passed > failed:
        ai_logs.append({
            "time": current_time,
            "level": "success",
            "msg": "Most recent test activity shows stable performance."
        })

    return ai_logs