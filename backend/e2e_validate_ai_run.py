import json
import time
from urllib import request, parse

BASE = "http://127.0.0.1:8001"
EMAIL = "e2e.tester2@example.com"
PASSWORD = "Test1234!"
TARGET_URL = "https://opensource-demo.orangehrmlive.com/"
INSTRUCTION = (
    "Act as a senior QA engineer. Analyze the login page, validate form behavior, "
    "check accessibility, capture screenshots, generate findings and recommendations."
)


def http_json(method: str, url: str, payload=None, headers=None):
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=req_headers, method=method)
    with request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


# 1) login
login = http_json("POST", f"{BASE}/api/auth/login", {"email": EMAIL, "password": PASSWORD})
token = login.get("token")
headers = {"Authorization": f"Bearer {token}"}

# 2) plan generation
plan = http_json(
    "POST",
    f"{BASE}/ai/plan",
    {"url": TARGET_URL, "instruction": INSTRUCTION, "test_type": "e2e"},
)

# 3) start test
start = http_json(
    "POST",
    f"{BASE}/api/tests/start",
    {
        "url": TARGET_URL,
        "project_name": "orangehrm-real-playwright",
        "test_type": "e2e",
        "ai_plan": plan,
    },
    headers=headers,
)

test_id = start.get("test_id")

# 4) poll
status = None
record = None
for _ in range(120):
    record = http_json("GET", f"{BASE}/api/tests/{test_id}", headers=headers)
    status = (record or {}).get("status")
    if status in {"completed", "failed"}:
        break
    time.sleep(2)

logs = (record or {}).get("stream_logs") or []
messages = "\n".join([(entry or {}).get("msg", "") for entry in logs])

has_fallback = "(Fallback)" in messages or "(Sim)" in messages
has_launch = any((entry or {}).get("msg", "").find("Launching Playwright") >= 0 for entry in logs)
has_open = any((entry or {}).get("msg", "").find("Opening ") >= 0 for entry in logs)
has_action = any((entry or {}).get("msg", "").find("Executing ") >= 0 for entry in logs)
has_screenshot_event = any((entry or {}).get("type") == "screenshot" for entry in logs)

result = {
    "test_id": test_id,
    "status": status,
    "overall_status": (record or {}).get("overall_status"),
    "health_score": (record or {}).get("health_score"),
    "has_report": bool((record or {}).get("report")),
    "bugs_count": len((record or {}).get("bugs") or []),
    "log_count": len(logs),
    "has_launch_log": has_launch,
    "has_open_log": has_open,
    "has_action_log": has_action,
    "has_screenshot_event": has_screenshot_event,
    "has_fallback": has_fallback,
    "screenshot_paths": (record or {}).get("screenshot_paths") or [],
    "ai_report_screenshots": (((record or {}).get("ai_report") or {}).get("screenshots") or []),
    "sample_record": {
        "test_id": (record or {}).get("test_id"),
        "status": (record or {}).get("status"),
        "screenshot_paths": (record or {}).get("screenshot_paths"),
        "ai_report_screenshots": (((record or {}).get("ai_report") or {}).get("screenshots") or []),
    },
}

print(json.dumps({"plan": plan, "validation": result}, indent=2))
