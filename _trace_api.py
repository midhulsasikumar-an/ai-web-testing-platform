import os, json, requests
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'

# Find the user record for the previously signed-up user
from backend.database.mongo import collection, client
db = client['ai-web-testing']
# user 18966c90-72f8-4b7c-9949-03d88c3a6b55 created a test 8dfb91c6
test = collection.find_one({'test_id': '8dfb91c6-68ba-45d5-916a-54b55f644f47'}, {'_id': 0, 'user_id': 1, 'status': 1})
print('Test found:', test)

# We need a JWT. Let me sign up a fresh user and get a token.
import random
email = f'trace_{random.randint(10000,99999)}@test.com'
print(f'\n=== Signup: {email} ===')
r = requests.post('http://localhost:8765/api/auth/signup', json={
    'email': email, 'password': 'Trace123!', 'name': 'Trace'
})
print('status:', r.status_code, 'body:', r.text[:200])
if r.status_code == 200:
    token = r.json().get('access_token') or r.json().get('token')
    print('got token (truncated):', token[:30] + '...')

    # Now hit GET /api/tests/{id} for the 8dfb91c6 test
    print('\n=== GET /api/tests/8dfb91c6... ===')
    r2 = requests.get('http://localhost:8765/api/tests/8dfb91c6-68ba-45d5-916a-54b55f644f47',
                       headers={'Authorization': f'Bearer {token}'})
    print('status:', r2.status_code)
    if r2.status_code == 200:
        d = r2.json()
        print('top-level keys:', list(d.keys()))
        print('status:', d.get('status'))
        print('overall_status:', d.get('overall_status'))
        print('stream_logs count:', len(d.get('stream_logs', [])))
        sl = d.get('stream_logs', [])
        # Show ALL stream_logs entries
        print('\n=== ALL STREAM LOGS ===')
        for i, e in enumerate(sl):
            t = e.get('type', '?')
            l = e.get('level', '?')
            m = e.get('msg', e.get('message', ''))[:120]
            print(f'  [{i:3d}] type={t:20s} level={l:8s} msg={m}')
    else:
        print('body:', r2.text[:500])
