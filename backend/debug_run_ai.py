import asyncio
import uuid
from datetime import datetime
from backend.services.test_services import run_ai_plan_and_update

async def main():
    test_id = str(uuid.uuid4())
    test_data = {
        "user_id": "local-debug",
        "execution_id": test_id,
        "test_id": test_id,
        "url": 'http://localhost:3000/',
        "project": 'debug',
        "test_type": 'ai',
        "status": 'running',
        "results": [],
        "stream_logs": [],
        "created_at": datetime.utcnow().isoformat(),
    }

    plan = {
        "test_case": {
            "title": "Debug Plan",
            "expected": "",
            "steps": [
                {"action": "click", "target": "Log In", "selector": ""}
            ]
        }
    }

    await run_ai_plan_and_update(test_data, 'http://localhost:3000/', 'local-debug', plan)

if __name__ == '__main__':
    asyncio.run(main())
