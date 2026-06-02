"""
Phase 1 trace: Run a real Saucedemo test using the AI PLAN path.

The AI plan path is the one that:
- Uses progress_callback to write stream_logs to Mongo on every event
- Has the "Execution finished" event being the last progress_callback write
- Then calls enforce_terminal_write for the final state

This is the path where the bug manifests.
"""
import os, json, time, requests, threading
from datetime import datetime
from collections import defaultdict

API = "http://127.0.0.1:8765"
LOG_FILE = "_server_p1.log"
TRACE_OUT = "_phase1_timeline_ai.json"

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
email = f"phase1ai_{int(time.time())}@test.com"
print(f"\n=== Signup: {email} ===")
r = requests.post(f"{API}/api/auth/signup", json={
    "email": email, "password": "Trace123!", "name": "Phase1AI"
})
log_event("signup", status=r.status_code)
token = r.json()["access_token"]
user_id = r.json()["user"]["id"]
print(f"  user_id={user_id}")

# Step 1: Generate an AI plan
print(f"\n=== Generate AI plan for saucedemo ===")
r = requests.post(f"{API}/ai/plan",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "url": "https://www.saucedemo.com/",
        "instruction": "log in with standard_user / secret_sauce, add the first product to cart, then verify cart shows 1 item",
        "test_type": "ai",
    })
log_event("ai_plan", status=r.status_code, body_len=len(r.text))
if r.status_code != 200:
    print(f"  ai_plan FAILED: {r.text[:500]}")
    raise SystemExit(1)
ai_plan = r.json()
print(f"  ai_plan received, keys: {list(ai_plan.keys())[:8]}")

# Step 2: Start a test WITH the ai_plan
print(f"\n=== Start test WITH ai_plan ===")
r = requests.post(f"{API}/api/tests/start",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "url": "https://www.saucedemo.com/",
        "test_name": "Phase1 Saucedemo AI Trace",
        "goal": "log in with standard_user / secret_sauce, add the first product to cart, then verify cart shows 1 item",
        "test_type": "ai",
        "browser": "chromium",
        "ai_plan": ai_plan,
    })
log_event("test_start", status=r.status_code, body=r.text[:300])
test_id = r.json()["test_id"]
print(f"  test_id={test_id}")

# Connect to Mongo
from pymongo import MongoClient
with open("backend/.env") as f:
    for line in f:
        if line.startswith("MONGO_URL="):
            MONGO_URL = line.split("=", 1)[1].strip()
            break
mc = MongoClient(MONGO_URL)
db = mc["ai-web-testing"]

# Polling loop
print(f"\n=== Polling test_id={test_id} (1s interval, max 5 min) ===")
poll_history = []
start = time.time()
last_mongo_status = None
last_mongo_logs_count = 0
last_api_status = None
last_api_logs_count = 0
mongo_first_terminal = None
api_first_terminal = None
api_first_terminal_log_count = None
mongo_first_terminal_log_count = None
mongo_stuck_in_running_with_finished_log = None

while time.time() - start < 300:
    elapsed = time.time() - start
    poll_ts = now_ms()
    mongo_doc = db.test_runs.find_one(
        {"test_id": test_id},
        {"_id": 0, "test_id": 1, "status": 1, "failure_reason": 1, "updated_at": 1, "created_at": 1,
         "stream_logs": 1, "results": 1}
    )
    if mongo_doc is None:
        time.sleep(1)
        continue

    mongo_status = mongo_doc.get("status")
    mongo_logs = mongo_doc.get("stream_logs") or []
    mongo_logs_count = len(mongo_logs)
    last_log = mongo_logs[-1] if mongo_logs else None
    last_log_summary = f"{last_log.get('type', '?')}:{last_log.get('msg', '')[:80]}" if last_log else "(empty)"
    has_terminal_summary = any(e.get("type") == "terminal_summary" for e in mongo_logs)
    has_execution_finished = any("Execution finished" in (e.get("msg") or "") for e in mongo_logs)

    # API state
    api_status_field = None
    api_logs_count = 0
    try:
        rr = requests.get(f"{API}/api/tests/{test_id}",
                          headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if rr.status_code == 200:
            d = rr.json()
            api_status_field = d.get("status")
            api_logs_count = len(d.get("stream_logs") or [])
    except Exception as exc:
        api_status_field = f"EXC:{type(exc).__name__}"

    mongo_terminal = mongo_status not in (None, "running", "pending", "cancel_requested", "")
    api_terminal = api_status_field not in (None, "running", "pending", "cancel_requested", "")

    if mongo_terminal and mongo_first_terminal is None:
        mongo_first_terminal = (elapsed, mongo_status, mongo_logs_count, has_terminal_summary, has_execution_finished)
    if api_terminal and api_first_terminal is None:
        api_first_terminal = (elapsed, api_status_field, api_logs_count, has_terminal_summary, has_execution_finished)

    # Detect the bug: Mongo status="running" but stream_logs contain "Execution finished" or terminal_summary
    if mongo_status == "running" and (has_execution_finished or has_terminal_summary):
        if mongo_stuck_in_running_with_finished_log is None:
            mongo_stuck_in_running_with_finished_log = (elapsed, mongo_status, mongo_logs_count, has_terminal_summary, has_execution_finished, last_log_summary)
            log_event("BUG_DETECTED_mongo_running_with_finished_log", elapsed_s=round(elapsed, 1),
                      status=mongo_status, logs_count=mongo_logs_count,
                      has_terminal_summary=has_terminal_summary, has_execution_finished=has_execution_finished,
                      last_log=last_log_summary)

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

    if mongo_terminal and api_terminal and (elapsed) > 5:
        log_event("both_terminal", elapsed_s=round(elapsed, 1),
                  mongo_status=mongo_status, api_status=api_status_field,
                  mongo_logs=mongo_logs_count, api_logs=api_logs_count)
        break

    time.sleep(1)

# Final state
print(f"\n=== Final state ===")
mongo_doc = db.test_runs.find_one({"test_id": test_id}, {"_id": 0})
mongo_status = mongo_doc.get("status")
mongo_logs = mongo_doc.get("stream_logs") or []
has_terminal_summary = any(e.get("type") == "terminal_summary" for e in mongo_logs)
has_execution_finished = any("Execution finished" in (e.get("msg") or "") for e in mongo_logs)

print(f"  mongo: status={mongo_status}, logs={len(mongo_logs)}, failure_reason={mongo_doc.get('failure_reason')}")
print(f"  has_terminal_summary={has_terminal_summary}, has_execution_finished={has_execution_finished}")
print(f"  mongo_first_terminal: {mongo_first_terminal}")
print(f"  api_first_terminal: {api_first_terminal}")
print(f"  bug_observed: {mongo_stuck_in_running_with_finished_log}")

# Last few log lines
print(f"\n=== Last 5 stream_logs ===")
for e in mongo_logs[-5:]:
    print(f"  type={e.get('type'):20s} level={e.get('level'):8s} msg={e.get('msg', '')[:120]}")

# Write timeline
with open(TRACE_OUT, "w") as f:
    json.dump({
        "test_id": test_id,
        "user_id": user_id,
        "duration_s": time.time() - start,
        "mongo_first_terminal": mongo_first_terminal,
        "api_first_terminal": api_first_terminal,
        "bug_observed": mongo_stuck_in_running_with_finished_log,
        "final_mongo_status": mongo_status,
        "final_failure_reason": mongo_doc.get("failure_reason"),
        "final_stream_logs_count": len(mongo_logs),
        "has_terminal_summary": has_terminal_summary,
        "has_execution_finished": has_execution_finished,
        "events": events,
    }, f, indent=2, default=str)

print(f"\n=== Wrote {TRACE_OUT} with {len(events)} events ===")
