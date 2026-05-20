import asyncio
import json
import httpx

BASE_URL = "http://localhost:8000/ai"

async def run_tests():
    print("🚀 Starting AI Workspace API Tests...")
    
    async with httpx.AsyncClient() as client:
        # 1. Test Chat
        print("\n--- 1. Testing AI Chat ---")
        chat_payload = {
            "user_id": "demo-user",
            "message": "Can you show me the Amazon report from yesterday?",
            "context": {
                "website": "amazon.com"
            }
        }
        resp = await client.post(f"{BASE_URL}/chat", json=chat_payload, timeout=20.0)
        print(f"Status: {resp.status_code}")
        print("Response:", json.dumps(resp.json(), indent=2))
        
        session_id = resp.json().get("session_id")
        
        # 2. Test Session Retrieval
        if session_id:
            print(f"\n--- 2. Testing Session Retrieval for {session_id} ---")
            resp = await client.get(f"{BASE_URL}/session/{session_id}")
            print(f"Status: {resp.status_code}")
            print("Session Data:", json.dumps(resp.json(), indent=2))
            
            # Follow-up question
            print("\n--- 3. Testing Contextual Follow-up Chat ---")
            followup_payload = {
                "session_id": session_id,
                "user_id": "demo-user",
                "message": "Now compare it with the latest run.",
                "context": {
                    "website": "amazon.com"
                }
            }
            resp = await client.post(f"{BASE_URL}/chat", json=followup_payload, timeout=20.0)
            print(f"Status: {resp.status_code}")
            print("Response:", json.dumps(resp.json(), indent=2))

        # 4. Test Retrieve Report
        print("\n--- 4. Testing Retrieve Report ---")
        resp = await client.post(f"{BASE_URL}/retrieve-report?query=Amazon report from last month")
        print(f"Status: {resp.status_code}")
        print("Response:", json.dumps(resp.json(), indent=2))

        # 5. Test Generate Workflow
        print("\n--- 5. Testing Workflow Generation ---")
        workflow_payload = {
            "user_id": "demo-user",
            "prompt": "Run accessibility testing every Monday at 8 PM for Amazon."
        }
        resp = await client.post(f"{BASE_URL}/generate-workflow", json=workflow_payload)
        print(f"Status: {resp.status_code}")
        print("Response:", json.dumps(resp.json(), indent=2))

        # 6. Test Recommendations
        print("\n--- 6. Testing AI Recommendations ---")
        resp = await client.get(f"{BASE_URL}/recommendations")
        print(f"Status: {resp.status_code}")
        print("Response:", json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(run_tests())
