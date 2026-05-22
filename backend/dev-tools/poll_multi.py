import requests, json, time, sys

sys.stdout.reconfigure(encoding='utf-8')

tests = {
    "Google": "53bb7b17-e3d3-4dff-a424-3b2b868c9c6d",
    "404 Page": "8ada019d-2d06-42fc-adb1-76727811c5a3"
}

BASE = "http://127.0.0.1:8000"

# Poll until all done
for i in range(25):
    all_done = True
    for name, tid in tests.items():
        r = requests.get(f"{BASE}/api/tests/{tid}")
        data = r.json()
        status = data.get("status", "unknown")
        if status not in ["completed", "failed"]:
            all_done = False
        print(f"  [{name}] status={status}")
    print(f"--- Poll {i+1} ---")
    if all_done:
        break
    time.sleep(3)

print()
print("=" * 60)

# Print final results
for name, tid in tests.items():
    r = requests.get(f"{BASE}/api/tests/{tid}")
    data = r.json()
    print(f"\n=== {name} ===")
    print(f"Status: {data['status']}")
    print(f"Health Score: {data.get('health_score', 'N/A')}")
    print(f"Summary: {data.get('summary', 'N/A')}")
    print(f"AI Summary: {data.get('ai_summary', 'N/A')}")
    print("Results:")
    for res in data.get("results", []):
        test_name = res.get("test", "?")
        test_status = res.get("status", "?")
        detail = res.get("details", res.get("error", ""))
        print(f"  - {test_name} => {test_status} {detail}")
    print(f"Insights: {json.dumps(data.get('insights', {}), indent=4)}")
    print(f"Recommendations: {data.get('recommendations', [])}")
