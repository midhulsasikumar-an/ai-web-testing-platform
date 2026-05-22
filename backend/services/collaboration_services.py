import uuid
import re
from datetime import datetime
from backend.database.mongo import thread_collection, comment_collection, decision_collection
from backend.services.activity_services import create_activity_event
from backend.services.notification_services import create_notification

def get_or_create_thread(object_type: str, object_id: str, created_by: str, title: str = None, workspace_id: str = None, project_id: str = None):
    thread = thread_collection.find_one({"object_type": object_type, "object_id": object_id}, {"_id": 0})
    if thread:
        return thread

    now = datetime.utcnow().isoformat()
    thread = {
        "thread_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "project_id": project_id,
        "object_type": object_type,
        "object_id": object_id,
        "title": title or f"Thread for {object_type} {object_id}",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "comment_count": 0,
        "last_activity_at": now
    }
    thread_collection.insert_one(thread)
    return thread

def get_thread_comments(thread_id: str):
    return list(comment_collection.find({"thread_id": thread_id}, {"_id": 0}).sort("created_at", 1))

def parse_mentions_from_body(body: str) -> list[str]:
    # Placeholder: Assuming mentions are like @username
    # In a real app, this would map usernames to user_ids by querying the users_collection
    mentions = re.findall(r'@(\w+)', body)
    return mentions

def create_comment(thread_id: str, author_id: str, body: str, parent_comment_id: str = None):
    thread = thread_collection.find_one({"thread_id": thread_id})
    if not thread:
        raise ValueError("Thread not found")

    mentions = parse_mentions_from_body(body)
    
    now = datetime.utcnow().isoformat()
    comment = {
        "comment_id": str(uuid.uuid4()),
        "thread_id": thread_id,
        "author_id": author_id,
        "body": body,
        "mentions": mentions,
        "attachments": [],
        "parent_comment_id": parent_comment_id,
        "is_decision": False,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None
    }
    comment_collection.insert_one(comment)

    thread_collection.update_one(
        {"thread_id": thread_id},
        {"$inc": {"comment_count": 1}, "$set": {"last_activity_at": now, "updated_at": now}}
    )

    create_activity_event(
        event_type="comment.created",
        object_type=thread["object_type"],
        object_id=thread["object_id"],
        actor_id=author_id,
        metadata={"comment_id": comment["comment_id"], "body_preview": body[:50]},
        workspace_id=thread.get("workspace_id"),
        project_id=thread.get("project_id")
    )

    for username in mentions:
        # In real app, look up user ID by username
        create_notification(
            user_id=username, # using username as ID for demo 
            type="mention",
            object_type=thread["object_type"],
            object_id=thread["object_id"],
            title="You were mentioned",
            message=f"{author_id} mentioned you",
            workspace_id=thread.get("workspace_id"),
            project_id=thread.get("project_id")
        )

    return comment

def mark_comment_as_decision(comment_id: str, actor_id: str):
    comment = comment_collection.find_one({"comment_id": comment_id})
    if not comment:
        raise ValueError("Comment not found")
        
    thread = thread_collection.find_one({"thread_id": comment["thread_id"]})

    comment_collection.update_one({"comment_id": comment_id}, {"$set": {"is_decision": True}})
    
    decision = {
        "decision_id": str(uuid.uuid4()),
        "thread_id": comment["thread_id"],
        "comment_id": comment_id,
        "object_type": thread["object_type"],
        "object_id": thread["object_id"],
        "decision_text": comment["body"],
        "created_by": actor_id,
        "created_at": datetime.utcnow().isoformat()
    }
    decision_collection.insert_one(decision)

    create_activity_event(
        event_type="comment.marked_as_decision",
        object_type=thread["object_type"],
        object_id=thread["object_id"],
        actor_id=actor_id,
        metadata={"decision_id": decision["decision_id"], "text": comment["body"][:50]}
    )
    return decision

def get_decisions(thread_id: str):
    return list(decision_collection.find({"thread_id": thread_id}, {"_id": 0}))
