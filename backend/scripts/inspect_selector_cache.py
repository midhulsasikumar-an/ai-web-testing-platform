from backend.database.mongo import selector_cache_collection
import json
from bson import ObjectId
import datetime

docs = list(selector_cache_collection.find().limit(20))
print('count=', selector_cache_collection.count_documents({}))
out = []
for d in docs:
    d2 = {}
    for k, v in d.items():
        if isinstance(v, ObjectId):
            d2[k] = str(v)
        elif isinstance(v, datetime.datetime):
            d2[k] = v.isoformat()
        else:
            d2[k] = v
    out.append(d2)
print(json.dumps(out, indent=2, default=str))
