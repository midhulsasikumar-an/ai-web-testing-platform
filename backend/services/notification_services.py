import uuid
from datetime import datetime
from backend.database.mongo import notification_collection

def create_notification(user_id: str, type: str, object_type: str, object_id: str, title: str, message: str, workspace_id: str = None, project_id: str = None):
    notification = {
        "notification_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "project_id": project_id,
        "user_id": user_id,
        "type": type,
        "object_type": object_type,
        "object_id": object_id,
        "title": title,
        "message": message,
        "read": False,
        "created_at": datetime.utcnow().isoformat()
    }
    notification_collection.insert_one(notification)
    return notification

def get_notifications(user_id: str):
    return list(notification_collection.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1))

def mark_notification_read(notification_id: str):
    notification_collection.update_one({"notification_id": notification_id}, {"$set": {"read": True}})
    return {"status": "success"}

def mark_all_read(user_id: str):
    notification_collection.update_many({"user_id": user_id}, {"$set": {"read": True}})
    return {"status": "success"}
