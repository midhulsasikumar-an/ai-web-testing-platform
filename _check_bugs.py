import os, json
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, bug_collection, client
db = client['ai-web-testing']
test_id = '8dfb91c6-68ba-45d5-916a-54b55f644f47'
uid = '18966c90-72f8-4b7c-9949-03d88c3a6b55'

print('=== bugs for test_id ===')
for b in bug_collection.find({'test_id': test_id, 'user_id': uid}, {'_id': 0, 'test_id': 1, 'title': 1, 'severity': 1, 'status': 1, 'fingerprint': 1, 'created_at': 1}):
    print(json.dumps(b, default=str))

print()
print('=== reports for test_id ===')
reports = db['reports']
for r in reports.find({'test_id': test_id}, {'_id': 0, 'test_id': 1, 'user_id': 1, 'status': 1, 'created_at': 1, 'updated_at': 1}):
    print(json.dumps(r, default=str))

print()
print('=== final test_runs doc (key fields) ===')
doc = collection.find_one({'test_id': test_id, 'user_id': uid}, {'_id': 0, 'status': 1, 'failure_reason': 1, 'created_at': 1, 'updated_at': 1, 'stream_logs_count': 1})
import json as J
print(J.dumps(doc, default=str, indent=2))
