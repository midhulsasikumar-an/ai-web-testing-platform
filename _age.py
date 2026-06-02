import os, json
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']

# Find the original "hung" run that took >1 hour.
# Look for runs with very old created_at AND/OR runs with stream_logs that
# captured the time span. Check the demo-user and runtime-validation users.
for uid in ['runtime-validation', 'demo-user']:
    print(f'\n=== user_id = {uid} ===')
    docs = list(collection.find(
        {'user_id': uid, 'status': {'$in': ['running', 'cancelled', 'failed', 'timed_out', 'completed', 'completed_with_failures']}},
        {'_id': 0, 'test_id': 1, 'status': 1, 'created_at': 1, 'updated_at': 1,
         'finished_at': 1, 'failure_reason': 1, 'stream_logs_count': {'$size': {'$ifNull': ['$stream_logs', []]}}}
    ).sort('created_at', 1))
    for d in docs:
        # compute age at update
        from datetime import datetime
        try:
            c = datetime.fromisoformat(str(d.get('created_at')).replace('Z', '+00:00'))
            u = datetime.fromisoformat(str(d.get('updated_at')).replace('Z', '+00:00'))
            age = (u - c).total_seconds()
        except Exception:
            age = None
        print(f"  test_id={d['test_id']} status={d['status']:25s} "
              f"created={d.get('created_at')} updated={d.get('updated_at')} "
              f"age={age}s stream_logs={d.get('stream_logs_count', 0)} "
              f"failure_reason={d.get('failure_reason')}")
