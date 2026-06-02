import os, json, requests
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'

# Read the JWT secret from .env
with open('backend/.env') as f:
    env = dict(line.strip().split('=', 1) for line in f if line.strip() and not line.startswith('#') and '=' in line)
JWT_SECRET = env.get('JWT_SECRET_KEY')
print('JWT secret loaded:', JWT_SECRET[:20] + '...')

# Use the same JWT library to mint a token for the original user
from backend.services.jwt_utils import _create_token
token = _create_token({'sub': '18966c90-72f8-4b7c-9949-03d88c3a6b55', 'user_id': '18966c90-72f8-4b7c-9949-03d88c3a6b55', 'email': 'trace@test.com'}, token_type='access', default_minutes=60) if False else __import__('backend.routes.auth_routes', fromlist=['create_access_token']).create_access_token({'sub': '18966c90-72f8-4b7c-9949-03d88c3a6b55', 'user_id': '18966c90-72f8-4b7c-9949-03d88c3a6b55', 'email': 'trace@test.com', 'id': '18966c90-72f8-4b7c-9949-03d88c3a6b55'})
print('Minted token (truncated):', token[:30] + '...')

# Now hit GET /api/tests/{id}
for tid in ['8dfb91c6-68ba-45d5-916a-54b55f644f47']:
    print(f'\n=== GET /api/tests/{tid} ===')
    r = requests.get(f'http://localhost:8765/api/tests/{tid}',
                     headers={'Authorization': f'Bearer {token}'})
    print('status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('top-level keys:', list(d.keys()))
        print('status:', d.get('status'))
        print('overall_status:', d.get('overall_status'))
        print('failure_reason:', d.get('failure_reason'))
        print('stream_logs count:', len(d.get('stream_logs', [])))
        sl = d.get('stream_logs', [])
        if sl:
            print('\n=== STREAM LOGS (last 20) ===')
            for i, e in enumerate(sl[-20:]):
                idx = len(sl) - 20 + i
                t = e.get('type', '?')
                l = e.get('level', '?')
                m = e.get('msg', e.get('message', ''))[:200]
                print(f'  [{idx:3d}] type={t:25s} level={l:8s} msg={m}')
            # Check the very LAST one
            print('\n=== LAST STREAM LOG (full) ===')
            last = sl[-1]
            print(json.dumps(last, indent=2, default=str)[:2000])
    else:
        print('body:', r.text[:500])

# Also check hung-diagnosis-run
print(f'\n\n=== GET /api/tests/hung-diagnosis-run ===')
r = requests.get('http://localhost:8765/api/tests/hung-diagnosis-run',
                 headers={'Authorization': f'Bearer {token}'})
print('status:', r.status_code)
if r.status_code == 200:
    d = r.json()
    print('top-level keys:', list(d.keys()))
    print('status:', d.get('status'))
    print('overall_status:', d.get('overall_status'))
    print('failure_reason:', d.get('failure_reason'))
    print('stream_logs count:', len(d.get('stream_logs', [])))
    sl = d.get('stream_logs', [])
    if sl:
        print('FIRST 5 stream_logs:')
        for i, e in enumerate(sl[:5]):
            t = e.get('type', '?')
            l = e.get('level', '?')
            m = e.get('msg', e.get('message', ''))[:200]
            print(f'  [{i:3d}] type={t:25s} level={l:8s} msg={m}')
        # Search for "Execution finished" or "terminal_summary" anywhere
        for i, e in enumerate(sl):
            if 'Execution finished' in str(e.get('msg', '')):
                print(f'\n*** FOUND "Execution finished" at index {i} ***')
                print(json.dumps(e, indent=2, default=str)[:2000])
            if e.get('type') == 'terminal_summary':
                print(f'\n*** FOUND terminal_summary at index {i} ***')
                print(json.dumps(e, indent=2, default=str)[:2000])
