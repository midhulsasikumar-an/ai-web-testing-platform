import os, json
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']

for tid in ['hung-diagnosis-run', 'saucedemo-orchestration-validation-2']:
    print(f'\n=== FULL DOC: {tid} ===')
    doc = collection.find_one({'test_id': tid}, {'_id': 0})
    if doc is None:
        print('NOT FOUND')
        continue
    # show key fields
    keys = ['test_id', 'user_id', 'status', 'created_at', 'updated_at', 'started_at',
            'finished_at', 'failure_reason', 'error', 'error_type', 'url', 'test_type',
            'project', 'browser', 'device', 'coverage_level', 'stream_logs', 'results',
            'summary', 'health_score', 'progress', 'scenario_count', 'completed_scenarios',
            'execution_id']
    for k in keys:
        v = doc.get(k)
        if v is not None:
            s = json.dumps(v, default=str)
            if len(s) > 800:
                s = s[:800] + '...'
            print(f'  {k}: {s}')
