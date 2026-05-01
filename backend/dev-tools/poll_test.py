import time
import requests

BASE_URL = "http://127.0.0.1:8000"

# Step 1: Start test
response = requests.post(f"{BASE_URL}/api/tests/start", json={
    "url": "https://example.com",
    "project_name": "Demo"
})

data = response.json()["data"]
test_id = data["test_id"]

print(f"Test started: {test_id}")

# Step 2: Poll status
while True:
    res = requests.get(f"{BASE_URL}/api/tests/{test_id}")
    test = res.json()

    print("Status:", test["status"])

    if test["status"] in ["completed", "failed"]:
        print("Final Result:", test["results"])
        break

    time.sleep(2)