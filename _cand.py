import os, json
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']

candidates = [
    'hung-diagnosis-run',
    'hang-diagnosis-run-2',
    'saucedemo-orchestration-validation',
    'saucedemo-orchestration-validation-2',
    'timeout-smoke-e4124c618c254d5f841dc16b610317b3',
    'timeout-smoke-9f75405fe7934bce8a90ea1d458c85bf',
    'timeout-smoke-cc5d0a71f9fc40a4998df4beddf7fb4f',
    'timeout-calibration-ea9f86ef3b8b43eaae2edf94e5e4f6db',
]

for tid in candidates:
    doc = collection.find_one(
        {'test_id': tid},
        {'_id': 0, 'test_id': 1, 'user_id': 1, 'status': 1, 'created_at': 1,
         'updated_at': 1, 'failure_reason': 1, 'url': 1, 'ai_plan': 1,
         'stream_logs_count': {'$size': {'$ifNull': ['$stream_logs', []]}},
         'results_count': {'$size': {'$ifNull': ['$results', []]}},
         'summary': 1, 'started_at': 1, 'finished_at': 1, 'error': 1}
    )
    if doc is None:
        print(f'=== {tid} ===')
        print('NOT FOUND IN DB')
        print()
        continue
    # has_ai_plan is a separate query
    has_plan = 'YES' if doc.get('ai_plan') else 'NO'
    if doc.get('ai_plan') and isinstance(doc['ai_plan'], dict):
        has_plan = f"YES (keys: {list(doc['ai_plan'].keys())[:5]})"
    print(f'=== {tid} ===')
    out = {k: v for k, v in doc.items() if k != 'ai_plan'}
    out['_has_ai_plan'] = has_plan
    print(json.dumps(out, default=str, indent=2)[:1500])
    print()
