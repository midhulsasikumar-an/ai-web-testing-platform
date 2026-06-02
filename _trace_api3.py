import os, json, requests, uuid
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'

# Sign up fresh user
import random
email = f'trace_{random.randint(10000,99999)}@test.com'
print(f'=== Signup: {email} ===')
r = requests.post('http://localhost:8765/api/auth/signup', json={
    'email': email, 'password': 'Trace123!', 'name': 'Trace'
})
print('status:', r.status_code)
d = r.json()
token = d.get('access_token') or d.get('token')
user_id = d.get('user', {}).get('user_id') or d.get('user', {}).get('id')
print('user_id:', user_id)

# Insert a fake test record for this user with terminal status and stream_logs
from backend.database.mongo import collection, client
db = client['ai-web-testing']
test_id = f'trace-{uuid.uuid4().hex[:8]}'
fake_test = {
    'test_id': test_id,
    'user_id': user_id,
    'status': 'completed_with_failures',
    'url': 'https://www.saucedemo.com/',
    'project': 'Trace Test',
    'test_type': 'ai',
    'ai_plan': {'summary': 'plan summary'},
    'stream_logs': [
        {'time': '00:01', 'level': 'info', 'msg': 'Test started', 'type': 'run_status'},
        {'time': '00:02', 'level': 'info', 'msg': 'Opening URL', 'type': 'run_status'},
        {'time': '00:03', 'level': 'info', 'msg': 'Browser launched', 'type': 'run_status'},
        {'time': '00:05', 'level': 'info', 'msg': 'Execution finished', 'type': 'run_status', 'details': {'status': 'completed_with_failures', 'run_status': 'completed_with_failures'}},
        {'time': '00:06', 'level': 'info', 'msg': '[SUCCESS] Test execution completed\n  Total Scenarios : 3\n  Passed          : 2\n  Failed          : 1\n  Screenshots     : 5\n  Duration        : 19.5s',
         'type': 'terminal_summary',
         'details': {'final_status': 'completed_with_failures', 'total_scenarios': 3, 'passed': 2, 'failed': 1, 'screenshots_captured': 5, 'duration_seconds': 19.5}},
    ],
    'results': [
        {'test': 'step 1', 'status': 'pass', 'details': 'page loaded'},
        {'test': 'step 2', 'status': 'fail', 'details': 'element not found'},
    ],
    'overall_status': 'warning',
    'created_at': '2026-06-02T14:00:00.000000',
    'updated_at': '2026-06-02T14:00:20.000000',
    'screenshot_paths': ['/api/screenshots/abc.png'],
}
collection.insert_one(fake_test.copy())
print(f'\n=== Inserted test_id: {test_id} ===')

# Now hit GET /api/tests/{id}
print(f'\n=== GET /api/tests/{test_id} ===')
r = requests.get(f'http://localhost:8765/api/tests/{test_id}',
                 headers={'Authorization': f'Bearer {token}'})
print('status:', r.status_code)
if r.status_code == 200:
    d = r.json()
    print('top-level keys:', list(d.keys()))
    print('\nstatus:', d.get('status'))
    print('overall_status:', d.get('overall_status'))
    print('failure_reason:', d.get('failure_reason'))
    print('stream_logs count:', len(d.get('stream_logs', [])))
    sl = d.get('stream_logs', [])
    if sl:
        print('\n=== ALL STREAM LOGS ===')
        for i, e in enumerate(sl):
            t = e.get('type', '?')
            l = e.get('level', '?')
            m = e.get('msg', e.get('message', ''))
            if len(m) > 100:
                m = m[:100] + '...'
            print(f'  [{i:3d}] type={t:20s} level={l:8s} msg={m}')

# Also test with 'running' status to demonstrate the live behavior
print(f'\n\n=== Testing "running" status — what does the page see? ===')
test_id2 = f'trace-{uuid.uuid4().hex[:8]}'
fake_test2 = fake_test.copy()
fake_test2['test_id'] = test_id2
fake_test2['status'] = 'running'
fake_test2['stream_logs'] = [
    {'time': '00:01', 'level': 'info', 'msg': 'Test started'},
    {'time': '00:02', 'level': 'info', 'msg': 'Opening URL'},
]
collection.insert_one(fake_test2)
r = requests.get(f'http://localhost:8765/api/tests/{test_id2}',
                 headers={'Authorization': f'Bearer {token}'})
print('status:', r.status_code, 'live status:', r.json().get('status'))

# Now INSERT a terminal_summary stream_log entry but KEEP status="running" — this simulates the bug
print(f'\n\n=== Simulating BUG: status="running" but stream_logs has "Execution finished" ===')
test_id3 = f'trace-{uuid.uuid4().hex[:8]}'
fake_test3 = fake_test.copy()
fake_test3['test_id'] = test_id3
fake_test3['status'] = 'running'  # <-- STATUS IS RUNNING
fake_test3['stream_logs'] = [
    {'time': '00:01', 'level': 'info', 'msg': 'Test started'},
    {'time': '00:02', 'level': 'info', 'msg': 'Execution finished', 'type': 'run_status'},  # <-- LOG SAYS FINISHED
    {'time': '00:03', 'level': 'info', 'msg': '[SUCCESS] Test execution completed', 'type': 'terminal_summary', 'details': {'final_status': 'completed'}},
]
collection.insert_one(fake_test3)
r = requests.get(f'http://localhost:8765/api/tests/{test_id3}',
                 headers={'Authorization': f'Bearer {token}'})
d = r.json()
print('GET returned status:', r.status_code, '| Mongo status:', d.get('status'))
print('stream_logs:')
for i, e in enumerate(d.get('stream_logs', [])):
    print(f'  [{i}] type={e.get("type")} level={e.get("level")} msg={e.get("msg")[:80]}')

# Clean up
collection.delete_many({'user_id': user_id})
print(f'\nCleaned up. Done.')
