import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb+srv://midhulsasikumarin_db_user:atlas_stock_2026@cluster1.z9yxifc.mongodb.net/?appName=Cluster1"
)

client = MongoClient(MONGO_URL)

# Your DB name
db = client["ai-web-testing"]

# Collections
collection = db["test_runs"]
bug_collection = db["bugs"]
users_collection = db["users"]

# Ensure unique email index
users_collection.create_index("email", unique=True)