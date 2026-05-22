import uuid
from datetime import datetime
from backend.database.mongo import workspace_collection, workspace_member_collection

def create_workspace(name: str, created_by: str):
    now = datetime.utcnow().isoformat()
    workspace = {
        "workspace_id": str(uuid.uuid4()),
        "name": name,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now
    }
    workspace_collection.insert_one(workspace)
    add_member(workspace["workspace_id"], created_by, "owner")
    return workspace

def get_workspaces():
    return list(workspace_collection.find({}, {"_id": 0}))

def get_workspace(workspace_id: str):
    return workspace_collection.find_one({"workspace_id": workspace_id}, {"_id": 0})

def add_member(workspace_id: str, user_id: str, role: str):
    member = {
        "membership_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role": role,
        "created_at": datetime.utcnow().isoformat()
    }
    workspace_member_collection.insert_one(member)
    return member

def get_members(workspace_id: str):
    return list(workspace_member_collection.find({"workspace_id": workspace_id}, {"_id": 0}))
