import os, json, sys
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']
test_id = '8dfb91c6-68ba-45d5-916a-54b55f644f47'
uid = '18966c90-72f8-4b7c-9949-03d88c3a6b55'

doc = collection.find_one({'test_id': test_id, 'user_id': uid}, {'_id': 0})
print(json.dumps(doc, default=str, indent=2)[:8000])
