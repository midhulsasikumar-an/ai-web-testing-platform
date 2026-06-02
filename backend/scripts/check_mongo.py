from backend.database.mongo import client, db

print('db=', db.name)
try:
    info = client.server_info()
    print('server_version=', info.get('version'))
    print('collections=', db.list_collection_names()[:20])
except Exception as e:
    print('server_info_error:', repr(e))
