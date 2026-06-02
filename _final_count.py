import os
os.environ['JWT_ALLOW_WEAK_SECRET'] = '1'
from backend.database.mongo import collection, client
db = client['ai-web-testing']
total = collection.count_documents({})
print(f'Total test_runs: {total}')
print(f'Currently running: {collection.count_documents({"status": "running"})}')
print(f'Currently pending: {collection.count_documents({"status": "pending"})}')
print(f'Currently cancel_requested: {collection.count_documents({"status": "cancel_requested"})}')
non_terminal_filter = {"status": {"$nin": ["completed", "completed_with_failures", "failed", "cancelled", "timed_out"]}}
print(f'Non-terminal (any): {collection.count_documents(non_terminal_filter)}')
# status distribution
print('\nStatus distribution:')
for d in collection.aggregate([{'$group': {'_id': '$status', 'count': {'$sum': 1}}}, {'$sort': {'count': -1}}]):
    print(f'  {d["_id"]}: {d["count"]}')
