import os, json
from datetime import datetime, timezone, timedelta
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']

# Find ALL test_runs, sort by created_at desc, show status distribution
total = collection.count_documents({})
print(f'TOTAL test_runs in DB: {total}')

# Distribution by status
pipeline = [
    {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
]
print('\n=== Status distribution ===')
for d in collection.aggregate(pipeline):
    print(f"  {d['_id']}: {d['count']}")

# Find any test_runs still in 'running' or 'pending' state
print('\n=== Currently non-terminal runs (status not in TERMINAL) ===')
TERMINAL = {'completed', 'completed_with_failures', 'failed', 'cancelled', 'timed_out'}
non_term = list(collection.find(
    {'status': {'$nin': list(TERMINAL)}},
    {'_id': 0, 'test_id': 1, 'user_id': 1, 'status': 1, 'created_at': 1,
     'updated_at': 1, 'failure_reason': 1, 'url': 1, 'ai_plan': 1}
).limit(20))
print(f'Found: {len(non_term)}')
for r in non_term:
    print(json.dumps(r, default=str))

# Find any runs with very old created_at (likely stuck)
print('\n=== Oldest 10 test_runs by created_at ===')
oldest = list(collection.find(
    {},
    {'_id': 0, 'test_id': 1, 'user_id': 1, 'status': 1, 'created_at': 1,
     'updated_at': 1, 'failure_reason': 1, 'ai_plan': 1, 'url': 1}
).sort('created_at', 1).limit(10))
for r in oldest:
    print(json.dumps(r, default=str))
