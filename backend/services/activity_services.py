import uuid
from datetime import datetime
from backend.database.mongo import activity_collection

def create_activity_event(event_type: str, object_type: str, object_id: str, actor_id: str, metadata: dict = None, workspace_id: str = None, project_id: str = None):
    event = {
        "event_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "project_id": project_id,
        "actor_id": actor_id,
        "event_type": event_type,
        "object_type": object_type,
        "object_id": object_id,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat()
    }
    activity_collection.insert_one(event)
    return event

def get_activity_events(object_type: str = None, object_id: str = None):
    query = {}
    if object_type and object_id:
        query = {"object_type": object_type, "object_id": object_id}
    events = list(activity_collection.find(query, {"_id": 0}).sort("created_at", -1))
    return events
