import uuid
from datetime import datetime
from backend.database.mongo import project_collection

def create_project(workspace_id: str, name: str, description: str, created_by: str):
    now = datetime.utcnow().isoformat()
    project = {
        "project_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "name": name,
        "description": description,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now
    }
    project_collection.insert_one(project)
    return project

def get_projects(workspace_id: str = None):
    query = {"workspace_id": workspace_id} if workspace_id else {}
    return list(project_collection.find(query, {"_id": 0}))

def get_project(project_id: str):
    return project_collection.find_one({"project_id": project_id}, {"_id": 0})
