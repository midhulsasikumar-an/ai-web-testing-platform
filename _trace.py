import os, json, time, sys
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
from backend.services.execution_watchdog import find_stuck_runs
db = client['ai-web-testing']
test_id = '8dfb91c6-68ba-45d5-916a-54b55f644f47'
uid = '18966c90-72f8-4b7c-9949-03d88c3a6b55'

def snap(label, projection=None):
    if projection is None:
        projection = {'_id': 0, 'test_id': 1, 'status': 1, 'created_at': 1, 'updated_at': 1,
                      'failure_reason': 1, 'scenario_count': 1, 'progress': 1,
                      'completed_scenarios': 1, 'started_at': 1, 'finished_at': 1,
                      'error': 1, 'error_type': 1, 'results_count': 1, 'stream_logs_count': 1}
    doc = collection.find_one({'test_id': test_id, 'user_id': uid}, projection)
    print(f'\n=== {label} ===')
    if not doc:
        print('NO DOCUMENT FOUND')
        return
    print(json.dumps(doc, default=str, indent=2)[:2500])

if len(sys.argv) > 1 and sys.argv[1] == 'stuck':
    stuck = find_stuck_runs(stall_seconds=300)
    print('Stuck runs (>300s old, non-terminal):')
    for r in stuck[:20]:
        print(f"  test_id={r.get('test_id')} status={r.get('status')} updated_at={r.get('updated_at')}")
else:
    snap(sys.argv[1] if len(sys.argv) > 1 else 'SNAPSHOT')
