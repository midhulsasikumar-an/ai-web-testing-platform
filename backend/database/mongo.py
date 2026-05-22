from pymongo import MongoClient

MONGO_URL = "mongodb+srv://midhulsasikumarin_db_user:atlas_stock_2026@cluster1.z9yxifc.mongodb.net/?appName=Cluster1"

client = MongoClient(MONGO_URL)

# Your DB name
db = client["ai-web-testing"]

# Your collection name
collection = db["test_runs"]
users_collection = db["users"]

# Collaboration Collections
workspace_collection = db["workspaces"]
project_collection = db["projects"]
workspace_member_collection = db["workspace_members"]
thread_collection = db["threads"]
comment_collection = db["comments"]
decision_collection = db["decisions"]
activity_collection = db["activity_events"]
notification_collection = db["notifications"]
review_collection = db["reviews"]
bugs_collection = db["bugs"]
