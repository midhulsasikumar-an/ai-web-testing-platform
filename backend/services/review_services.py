import uuid
from datetime import datetime
from backend.database.mongo import review_collection
from backend.services.activity_services import create_activity_event
from backend.services.notification_services import create_notification

def request_review(object_type: str, object_id: str, reviewer_id: str, requester_id: str, workspace_id: str = None, project_id: str = None):
    now = datetime.utcnow().isoformat()
    review = {
        "review_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "project_id": project_id,
        "object_type": object_type,
        "object_id": object_id,
        "reviewer_id": reviewer_id,
        "status": "pending",
        "comment": None,
        "created_at": now,
        "updated_at": now
    }
    review_collection.insert_one(review)
    
    create_activity_event(
        event_type="review.requested",
        object_type=object_type,
        object_id=object_id,
        actor_id=requester_id,
        metadata={"reviewer_id": reviewer_id}
    )
    
    create_notification(
        user_id=reviewer_id,
        type="review_request",
        object_type=object_type,
        object_id=object_id,
        title="Review Requested",
        message=f"{requester_id} requested your review."
    )
    return review

def update_review_status(review_id: str, status: str, actor_id: str, comment: str = None):
    review = review_collection.find_one({"review_id": review_id})
    if not review:
        raise ValueError("Review not found")
        
    review_collection.update_one(
        {"review_id": review_id},
        {"$set": {"status": status, "comment": comment, "updated_at": datetime.utcnow().isoformat()}}
    )
    
    create_activity_event(
        event_type=f"review.{status}",
        object_type=review["object_type"],
        object_id=review["object_id"],
        actor_id=actor_id,
        metadata={"review_id": review_id, "comment": comment}
    )
    return {"status": "success"}

def get_reviews(object_type: str, object_id: str):
    return list(review_collection.find({"object_type": object_type, "object_id": object_id}, {"_id": 0}))
