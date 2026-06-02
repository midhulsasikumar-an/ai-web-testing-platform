import os, json, sys
from datetime import datetime, timezone, timedelta
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']
uid = '18966c90-72f8-4b7c-9949-03d88c3a6b55'

# All test_runs for this user, sorted by created_at desc
all_runs = list(collection.find(
    {'user_id': uid},
    {'_id': 0, 'test_id': 1, 'status': 1, 'created_at': 1, 'updated_at': 1,
     'failure_reason': 1, 'url': 1, 'test_type': 1, 'ai_plan': 1,
     'summary': 1, 'results': 1}
).sort('created_at', -1))

print(f'Total test_runs for this user: {len(all_runs)}')
print()
for r in all_runs:
    print(json.dumps({k: r.get(k) for k in
                      ['test_id', 'status', 'created_at', 'updated_at',
                       'failure_reason', 'url', 'test_type', 'ai_plan']},
                     default=str))
    if isinstance(r.get('summary'), dict):
        print(f"  summary: {r['summary']}")
    if r.get('results'):
        if isinstance(r['results'], list) and r['results'] and isinstance(r['results'][0], dict):
            err = r['results'][0].get('error', '')
            if err:
                print(f"  results[0].error: {err[:200]}")
    print()
