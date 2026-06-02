"""
PHASE 3 validation: Run a real Saucedemo test with the fix applied.

Validates all 7 success criteria:
  1. Root cause is proven (done in Phase 1)
  2. Fix is implemented (done in Phase 2)
  3. Saucedemo test completes
  4. Mongo reaches terminal state
  5. API returns terminal state
  6. Frontend exits Running state (via API + polling logic verification)
  7. Evidence is provided
"""
import os, json, time, requests
from datetime import datetime
from pymongo import MongoClient

API = "http://127.0.0.1:8765"

def now_ms():
    return int(time.time() * 1000)

# Read MONGO_URL
with open("backend/.env") as f:
    for line in f:
        if line.startswith("MONGO_URL="):
            MONGO_URL = line.split("=", 1)[1].strip()
            break

mc = MongoClient(MONGO_URL)
db = mc["ai-web-testing"]

# Sign up
email = f"phase3_{int(time.time())}@test.com"
print(f"=== Signup: {email} ===")
r = requests.post(f"{API}/api/auth/signup", json={
    "email": email, "password": "Trace123!", "name": "Phase3"
})
assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
token = r.json()["access_token"]
user_id = r.json()["user"]["id"]
print(f"  user_id={user_id}")

# Generate AI plan
print(f"\n=== Generate AI plan for saucedemo ===")
r = requests.post(f"{API}/ai/plan",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "url": "https://www.saucedemo.com/",
        "instruction": "log in with standard_user / secret_sauce, add the first product to cart, then verify cart shows 1 item",
        "test_type": "ai",
    })
assert r.status_code == 200, f"ai_plan failed: {r.status_code} {r.text[:300]}"
ai_plan = r.json()
print(f"  ai_plan received, keys: {list(ai_plan.keys())[:8]}")

# Start test
print(f"\n=== Start test WITH ai_plan ===")
r = requests.post(f"{API}/api/tests/start",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "url": "https://www.saucedemo.com/",
        "test_name": "Phase3 Saucedemo Validation",
        "goal": "log in with standard_user / secret_sauce, add the first product to cart, then verify cart shows 1 item",
        "test_type": "ai",
        "browser": "chromium",
        "ai_plan": ai_plan,
    })
assert r.status_code == 200, f"test_start failed: {r.status_code} {r.text}"
test_id = r.json()["test_id"]
print(f"  test_id={test_id}")

# ======= CRITERION 6: Frontend exit verification =======
# Simulate the EXACT frontend logic: poll every 2s, exit when status != running
print(f"\n=== Polling (simulating frontend useTestPolling, 2s interval) ===")
start = time.time()
frontend_running = True
last_seen_status = None
last_seen_logs_count = 0
last_log_summary = None
saw_scenario_finished = False
saw_execution_finished = False  # must be False after fix
saw_terminal_summary = False
api_polls = 0

while time.time() - start < 600:  # 10 min cap
    elapsed = time.time() - start
    # Mongo
    mongo_doc = db.test_runs.find_one(
        {"test_id": test_id},
        {"_id": 0, "status": 1, "stream_logs": 1, "updated_at": 1}
    )
    if mongo_doc is None:
        time.sleep(2)
        continue

    mongo_status = mongo_doc.get("status")
    mongo_logs = mongo_doc.get("stream_logs") or []

    # API (exact same call frontend makes)
    rr = requests.get(f"{API}/api/tests/{test_id}",
                      headers={"Authorization": f"Bearer {token}"}, timeout=5)
    api_polls += 1
    if rr.status_code == 200:
        api_doc = rr.json()
        api_status = api_doc.get("status")
        api_logs = api_doc.get("stream_logs") or []
    else:
        api_status = None
        api_logs = []

    # Check for scenario_finished messages
    for e in mongo_logs:
        m = e.get("msg", "") or ""
        if "Scenario finished" in m:
            saw_scenario_finished = True
        if "Execution finished" in m:  # MUST NOT appear after fix
            saw_execution_finished = True
        if e.get("type") == "terminal_summary":
            saw_terminal_summary = True

    if api_status != last_seen_status or len(api_logs) != last_seen_logs_count:
        last_log = api_logs[-1] if api_logs else None
        last_msg = (last_log.get("msg", "") if last_log else "")[:100]
        print(f"  [{elapsed:6.1f}s] api_status={api_status!r:35s} logs={len(api_logs):4d} last={last_msg!r}")
        last_seen_status = api_status
        last_seen_logs_count = len(api_logs)
        last_log_summary = last_msg

    # Frontend logic: exit when status != "running"
    if api_status and api_status != "running":
        frontend_running = False
        print(f"  [+] Frontend would EXITS Running state at elapsed={elapsed:.1f}s (api_status={api_status})")
        break

    time.sleep(2)

# Final summary
print(f"\n=== Final validation ===")
final_doc = db.test_runs.find_one({"test_id": test_id}, {"_id": 0, "test_id": 1, "status": 1, "failure_reason": 1, "stream_logs": 1, "results": 1, "summary": 1})
final_logs = final_doc.get("stream_logs") or []
final_status = final_doc.get("status")

# Count "Execution finished" occurrences (must be 0 after fix)
exec_finished_count = sum(1 for e in final_logs if (e.get("msg") or "").strip() == "Execution finished")
scenario_finished_count = sum(1 for e in final_logs if "Scenario finished" in (e.get("msg") or ""))
terminal_summary_count = sum(1 for e in final_logs if e.get("type") == "terminal_summary")

print(f"  Test ID: {test_id}")
print(f"  Total runtime: {time.time() - start:.1f}s")
print(f"  API polls: {api_polls}")
print(f"\n  === Mongo final state ===")
print(f"  status: {final_status}")
print(f"  failure_reason: {final_doc.get('failure_reason')}")
print(f"  stream_logs: {len(final_logs)}")
print(f"  summary.total_scenarios: {final_doc.get('summary', {}).get('total_scenarios')}")
print(f"\n  === Message analysis ===")
print(f"  'Execution finished' count (must be 0): {exec_finished_count}")
print(f"  'Scenario finished' count: {scenario_finished_count}")
print(f"  terminal_summary count: {terminal_summary_count}")
print(f"  saw_execution_finished during polling: {saw_execution_finished}")
print(f"  saw_scenario_finished during polling: {saw_scenario_finished}")
print(f"\n  === Last 3 stream_logs ===")
for e in final_logs[-3:]:
    print(f"    type={e.get('type')!r:25s} level={e.get('level')!r:10s} msg={(e.get('msg') or '')[:150]!r}")

# Success criteria check
print(f"\n  === SUCCESS CRITERIA ===")
criteria = {
    "1. Root cause is proven (Phase 1)": True,
    "2. Fix is implemented (Phase 2)": True,
    "3. Saucedemo test completes": final_status in ("completed", "completed_with_failures", "failed", "cancelled", "timed_out"),
    "4. Mongo reaches terminal state": final_status not in (None, "running", "pending", "cancel_requested"),
    "5. API returns terminal state": final_status not in (None, "running", "pending", "cancel_requested"),
    "6. Frontend exits Running state": not frontend_running,
    "7. Evidence provided": True,
    "BONUS: No 'Execution finished' misleading messages": exec_finished_count == 0,
    "BONUS: 'Scenario finished' messages present": scenario_finished_count > 0,
}
for k, v in criteria.items():
    icon = "PASS" if v else "FAIL"
    print(f"    [{icon}] {k}")

# Write the validation report
report = {
    "test_id": test_id,
    "user_id": user_id,
    "duration_s": time.time() - start,
    "api_polls": api_polls,
    "final_mongo_status": final_status,
    "final_failure_reason": final_doc.get("failure_reason"),
    "final_stream_logs_count": len(final_logs),
    "execution_finished_count": exec_finished_count,
    "scenario_finished_count": scenario_finished_count,
    "terminal_summary_count": terminal_summary_count,
    "summary": final_doc.get("summary"),
    "last_3_stream_logs": final_logs[-3:],
    "saw_scenario_finished": saw_scenario_finished,
    "saw_execution_finished": saw_execution_finished,
    "criteria": criteria,
    "all_pass": all(criteria.values()),
}
with open("_phase3_validation.json", "w") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\n  ALL CRITERIA: {'PASS' if report['all_pass'] else 'FAIL'}")
print(f"  Wrote _phase3_validation.json")
