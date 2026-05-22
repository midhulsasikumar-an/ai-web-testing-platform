import requests, json, sys

sys.stdout.reconfigure(encoding='utf-8')

base = "http://127.0.0.1:8000"

urls = [
    ("https://news.ycombinator.com/", "Hacker News"),
    ("https://www.reddit.com/", "Reddit"),
    ("https://httpbin.org/status/500", "HTTPBin 500")
]

results = []
for url, name in urls:
    try:
        r = requests.post(f"{base}/api/tests/start", json={"url": url, "project_name": name})
        data = r.json()
        test_id = data.get("test_id")
        print(f"Started {name}: {test_id}")
        results.append((name, test_id))
    except Exception as e:
        print(f"Failed to start {name}: {e}")

with open("backend/dev-tools/active_tests.json", "w") as f:
    json.dump(results, f)
