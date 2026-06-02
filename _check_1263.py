import os, json
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from pymongo import MongoClient
with open('backend/.env') as f:
    for line in f:
        if line.startswith('MONGO_URL='):
            MONGO_URL = line.split('=', 1)[1].strip()
            break
mc = MongoClient(MONGO_URL)
db = mc['ai-web-testing']
d = db.test_runs.find_one({'test_id': '79a4e729-dbe1-41d2-9d84-f30f988fefab'}, {'_id': 0, 'test_id': 1, 'status': 1, 'created_at': 1, 'updated_at': 1, 'stream_logs': 1, 'summary': 1})
print('Status:', d.get('status'))
print('Created:', d.get('created_at'))
print('Updated:', d.get('updated_at'))
sl = d.get('stream_logs') or []
count = sum(1 for e in sl if 'Execution finished' in (e.get('msg') or ''))
print('Total stream_logs:', len(sl))
print("'Execution finished' count:", count)
print('Has terminal_summary:', any(e.get('type') == 'terminal_summary' for e in sl))
print('Last 5:')
for e in sl[-5:]:
    t = str(e.get('type') or '')
    l = str(e.get('level') or '')
    m = str(e.get('msg') or '')[:120]
    print('  type=' + t + ' level=' + l + ' msg=' + m)
