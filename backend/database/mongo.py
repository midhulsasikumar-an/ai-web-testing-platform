from pymongo import MongoClient

MONGO_URL = "mongodb+srv://midhulsasikumarin_db_user:atlas_stock_2026@cluster1.z9yxifc.mongodb.net/?appName=Cluster1"

client = MongoClient(MONGO_URL)

# Your DB name
db = client["ai-web-testing"]

# Your collection name
collection = db["test_runs"]