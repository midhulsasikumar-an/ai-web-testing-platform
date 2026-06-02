"""
Phase 1 trace: Run a real Saucedemo test and capture the full lifecycle.

Captures:
- All Mongo state changes (via direct polling)
- Server-side writes (via _server_p1.log grep)
- API responses (via /api/tests/{id} polling)
- Timeline of events
"""
import os, json, time, requests, threading
from datetime import datetime
from collections import defaultdict

API = "http://127.0.0.1:8765"
LOG_FILE = "_server_p1.log"
TRACE_OUT = "_phase1_timeline.json"

events = []
event_lock = threading.Lock()

def now_ms():
    return int(time.time() * 1000)

def log_event(category, **kw):
    ts = now_ms()
    e = {"ts_ms": ts, "ts_iso": datetime.utcnow().isoformat() + "Z", "category": category, **kw}
    with event_lock:
        events.append(e)
    print(f"  [{ts}] {category}: {kw}", flush=True)

# Sign up
email = f"phase1_{int(time.time())}@test.com"
print(f"\n=== Signup: {email} ===")
r = requests.post(f"{API}/api/auth/signup", json={
    "email": email, "password": "Trace123!", "name": "Phase1"
})
log_event("signup", status=r.status_code, body=r.text[:200])
token = r.json()["access_token"]
user_id = r.json()["user"]["id"]
print(f"  user_id={user_id}")

# Start a test
print(f"\n=== Start test against saucedemo ===")
r = requests.post(f"{API}/api/tests/start",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "url": "https://www.saucedemo.com/",
        "test_name": "Phase1 Saucedemo Trace",
        "goal": "log in with standard_user / secret_sauce, add the first product to cart, then verify cart shows 1 item",
        "test_type": "ai",
        "browser": "chromium",
    })
log_event("test_start", status=r.status_code, body=r.text)
test_id = r.json()["test_id"]
print(f"  test_id={test_id}")

# Connect to Mongo via the running server's process to read state
# Use the same library the server uses
from pymongo import MongoClient
import os as _os
_os.environ.setdefault("MONGO_URL", "")
# Read MONGO_URL from backend/.env
with open("backend/.env") as f:
    for line in f:
        if line.startswith("MONGO_URL="):
            MONGO_URL = line.split("=", 1)[1].strip()
            break

print(f"  MONGO_URL loaded (truncated): {MONGO_URL[:40]}...")

mc = MongoClient(MONGO_URL)
db = mc["ai-web-testing"]

# Polling loop: capture Mongo state + API state every 1s
print(f"\n=== Polling test_id={test_id} (1s interval, max 5 min) ===")
poll_history = []
start = time.time()
last_api_status = None
last_api_logs_count = 0
last_mongo_status = None
last_mongo_logs_count = 0
api_first_terminal = None
mongo_first_terminal = None

while time.time() - start < 300:  # 5 min
    elapsed = time.time() - start
    poll_ts = now_ms()
    # Mongo state
    mongo_doc = db.test_runs.find_one(
        {"test_id": test_id},
        {"_id": 0, "test_id": 1, "status": 1, "failure_reason": 1, "updated_at": 1, "created_at": 1,
         "stream_logs": 1, "results": 1}
    )
    if mongo_doc is None:
        log_event("poll", elapsed_s=round(elapsed, 1), mongo="NOT_FOUND")
        time.sleep(1)
        continue

    mongo_status = mongo_doc.get("status")
    mongo_logs = mongo_doc.get("stream_logs") or []
    mongo_logs_count = len(mongo_logs)
    last_log = mongo_logs[-1] if mongo_logs else None
    last_log_summary = f"{last_log.get('type', '?')}:{last_log.get('msg', '')[:60]}" if last_log else "(empty)"
    has_terminal_summary = any(e.get("type") == "terminal_summary" for e in mongo_logs)
    has_execution_finished = any("Execution finished" in (e.get("msg") or "") for e in mongo_logs)

    # API state
    api_status = "ERR"
    api_status_field = "ERR"
    api_logs_count = 0
    try:
        rr = requests.get(f"{API}/api/tests/{test_id}",
                          headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if rr.status_code == 200:
            d = rr.json()
            api_status = "OK"
            api_status_field = d.get("status")
            api_logs_count = len(d.get("stream_logs") or [])
    except Exception as exc:
        api_status = f"EXC:{type(exc).__name__}"

    mongo_terminal = mongo_status not in (None, "running", "pending", "cancel_requested", "")
    api_terminal = api_status_field not in (None, "running", "pending", "cancel_requested", "")

    if mongo_terminal and mongo_first_terminal is None:
        mongo_first_terminal = (elapsed, mongo_status, mongo_logs_count)
    if api_terminal and api_first_terminal is None:
        api_first_terminal = (elapsed, api_status_field, api_logs_count)

    # Log state changes
    if mongo_status != last_mongo_status:
        log_event("mongo_status_change", elapsed_s=round(elapsed, 1), new_status=mongo_status,
                  failure_reason=mongo_doc.get("failure_reason"),
                  logs_count=mongo_logs_count, last_log=last_log_summary,
                  has_terminal_summary=has_terminal_summary,
                  has_execution_finished=has_execution_finished)
        last_mongo_status = mongo_status
    elif mongo_logs_count != last_mongo_logs_count:
        log_event("mongo_logs_grew", elapsed_s=round(elapsed, 1),
                  status=mongo_status, logs_count=mongo_logs_count,
                  new_last_log=last_log_summary,
                  has_terminal_summary=has_terminal_summary,
                  has_execution_finished=has_execution_finished)
        last_mongo_logs_count = mongo_logs_count
    if api_status_field != last_api_status:
        log_event("api_status_change", elapsed_s=round(elapsed, 1), new_status=api_status_field,
                  api_logs_count=api_logs_count, http=rr.status_code)
        last_api_status = api_status_field

    if mongo_terminal and api_terminal and (time.time() - start - elapsed) > 3:
        log_event("both_terminal", elapsed_s=round(elapsed, 1),
                  mongo_status=mongo_status, api_status=api_status_field,
                  mongo_logs=mongo_logs_count, api_logs=api_logs_count)
        break

    time.sleep(1)

# Final state
print(f"\n=== Final state ===")
mongo_doc = db.test_runs.find_one({"test_id": test_id}, {"_id": 0})
print(f"  mongo: status={mongo_doc.get('status')}, logs={len(mongo_doc.get('stream_logs') or [])}, failure_reason={mongo_doc.get('failure_reason')}")
print(f"  mongo_first_terminal: {mongo_first_terminal}")
print(f"  api_first_terminal: {api_first_terminal}")

# Write timeline
with open(TRACE_OUT, "w") as f:
    json.dump({
        "test_id": test_id,
        "user_id": user_id,
        "duration_s": time.time() - start,
        "mongo_first_terminal_at_s": mongo_first_terminal[0] if mongo_first_terminal else None,
        "mongo_first_terminal_status": mongo_first_terminal[1] if mongo_first_terminal else None,
        "api_first_terminal_at_s": api_first_terminal[0] if api_first_terminal else None,
        "api_first_terminal_status": api_first_terminal[1] if api_first_terminal else None,
        "final_mongo_status": mongo_doc.get("status"),
        "final_failure_reason": mongo_doc.get("failure_reason"),
        "final_stream_logs_count": len(mongo_doc.get("stream_logs") or []),
        "events": events,
    }, f, indent=2, default=str)

print(f"\n=== Wrote {TRACE_OUT} with {len(events)} events ===")
