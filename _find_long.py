import os
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from pymongo import MongoClient
from datetime import datetime
with open('backend/.env') as f:
    for line in f:
        if line.startswith('MONGO_URL='):
            MONGO_URL = line.split('=', 1)[1].strip()
            break
mc = MongoClient(MONGO_URL)
db = mc['ai-web-testing']

# Find tests with duration > 5 min
docs = list(db.test_runs.find(
    {'user_id': {'$ne': 'runtime-validation'}, 'status': 'completed_with_failures'},
    {'_id': 0, 'test_id': 1, 'status': 1, 'created_at': 1, 'updated_at': 1, 'stream_logs_count': {'$size': {'$ifNull': ['$stream_logs', []]}}}
).sort('updated_at', -1).limit(10))
for d in docs:
    try:
        c = datetime.fromisoformat(str(d.get('created_at')).replace('Z', '+00:00'))
        u = datetime.fromisoformat(str(d.get('updated_at')).replace('Z', '+00:00'))
        age = (u - c).total_seconds()
    except Exception:
        age = None
    print(f"  test_id={d['test_id']} status={d.get('status')} age={age}s logs={d.get('stream_logs_count')}")

# Also find tests that are stuck in 'running'
print('\n\nCurrently running (excluding runtime-validation):')
for d in db.test_runs.find({'status': 'running'}, {'_id': 0, 'test_id': 1, 'created_at': 1, 'updated_at': 1, 'user_id': 1}):
    print(f"  test_id={d['test_id']} user={d.get('user_id')} created={d.get('created_at')} updated={d.get('updated_at')}")

print('\n\nTests with old updated_at but still non-terminal:')
from datetime import datetime, timedelta, timezone
cutoff = (datetime.now(timezone.utc) - timedelta(seconds=300)).isoformat()
for d in db.test_runs.find({'status': 'running', 'updated_at': {'$lt': cutoff}}, {'_id': 0, 'test_id': 1, 'created_at': 1, 'updated_at': 1, 'user_id': 1}):
    print(f"  test_id={d['test_id']} user={d.get('user_id')} created={d.get('created_at')} updated={d.get('updated_at')}")
