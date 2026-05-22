import requests, json, time, sys

sys.stdout.reconfigure(encoding='utf-8')

base = "http://127.0.0.1:8000"

try:
    with open("backend/dev-tools/active_tests.json", "r") as f:
        tests = json.load(f)
except FileNotFoundError:
    print("No active tests found file.")
    sys.exit(1)

# Poll until all done
for i in range(30):
    all_done = True
    for name, tid in tests:
        if not tid:
            continue
        r = requests.get(f"{base}/api/tests/{tid}")
        data = r.json()
        status = data.get("status", "unknown")
        if status not in ["completed", "failed"]:
            all_done = False
        print(f"  [{name}] status={status}")
    print(f"--- Poll {i+1} ---")
    if all_done:
        break
    time.sleep(5)

print()
print("=" * 60)
print("FINAL RESULTS")
print("=" * 60)

# Print final results
for name, tid in tests:
    if not tid:
        print(f"\n=== {name} ===\nFailed to start.")
        continue
    r = requests.get(f"{base}/api/tests/{tid}")
    data = r.json()
    print(f"\n=== {name} ===")
    print(f"URL: {data.get('url')}")
    print(f"Status: {data['status']}")
    print(f"Health Score: {data.get('health_score', 'N/A')}/100")
    print(f"AI Summary: {data.get('ai_summary', 'N/A')}")
    print("Results:")
    for res in data.get("results", []):
        test_name = res.get("test", "?")
        test_status = res.get("status", "?")
        detail = res.get("details", res.get("error", ""))
        print(f"  - {test_name} => {test_status} {detail}")
    
    insights = data.get("insights", {})
    print(f"Critical Issues: {insights.get('critical', [])}")
    print(f"Moderate Issues: {insights.get('moderate', [])}")
    print(f"Minor Issues: {insights.get('minor', [])}")
    print(f"Recommendations: {data.get('recommendations', [])}")
