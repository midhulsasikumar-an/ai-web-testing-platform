import asyncio
import os
import json

# ensure project root is on path
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.services.test_services import run_ai_plan_and_update, create_test_run
from backend.services.ai_plan_service import generate_test_plan
from backend.database.mongo import users_collection
from datetime import datetime

async def main():
    url = 'https://opensource-demo.orangehrmlive.com/'
    instruction = 'Perform login testing and dashboard validation.'
    plan = await generate_test_plan(url, instruction, 'e2e')
    # create a fake user id
    user_id = 'debug-user'
    # create test_data
    test_data = {
        'user_id': user_id,
        'execution_id': 'debug-run-1',
        'test_id': 'debug-run-1',
        'url': url,
        'project': 'debug',
        'test_type': 'e2e',
        'status': 'running',
        'results': [],
        'stream_logs': [],
        'screenshot': None,
        'summary': None,
        'health_score': None,
        'overall_status': None,
        'insights': None,
        'priority_issues': [],
        'recommendations': [],
        'report': None,
        'ai_summary': None,
        'bugs': [],
        'ai_plan': plan,
        'created_at': datetime.utcnow().isoformat()
    }

    try:
        await run_ai_plan_and_update(test_data, url, user_id, plan)
        print('run_ai_plan_and_update completed')
        print(json.dumps(test_data, indent=2, default=str)[:4000])
    except Exception as e:
        print('Exception during run:', e)

if __name__ == '__main__':
    asyncio.run(main())
