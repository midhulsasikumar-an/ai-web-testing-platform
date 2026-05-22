from fastapi import APIRouter, HTTPException
from backend.models.collaboration_schema import (
    ThreadOut, CommentCreate, CommentOut, DecisionOut, ActivityEventOut, NotificationOut, ReviewCreate, ReviewOut
)
from backend.services.collaboration_services import (
    get_or_create_thread, get_thread_comments, create_comment, mark_comment_as_decision, get_decisions
)
from backend.services.activity_services import get_activity_events
from backend.services.notification_services import get_notifications, mark_notification_read, mark_all_read
from backend.services.review_services import request_review, update_review_status, get_reviews

router = APIRouter()
mock_user_id = "mock_user_123"

# Thread APIs
@router.post("/threads/{object_type}/{object_id}", response_model=ThreadOut)
def api_get_or_create_thread(object_type: str, object_id: str, title: str = None):
    return get_or_create_thread(object_type, object_id, mock_user_id, title)

@router.get("/threads/{object_type}/{object_id}", response_model=ThreadOut)
def api_get_thread(object_type: str, object_id: str):
    # Same as POST for simplicity, it creates if not exists
    return get_or_create_thread(object_type, object_id, mock_user_id)

# Comment APIs
@router.get("/threads/{thread_id}/comments", response_model=list[CommentOut])
def api_get_comments(thread_id: str):
    return get_thread_comments(thread_id)

@router.post("/threads/{thread_id}/comments", response_model=CommentOut)
def api_create_comment(thread_id: str, comment: CommentCreate):
    return create_comment(thread_id, mock_user_id, comment.body, comment.parent_comment_id)

@router.post("/comments/{comment_id}/decision", response_model=DecisionOut)
def api_mark_decision(comment_id: str):
    return mark_comment_as_decision(comment_id, mock_user_id)

@router.get("/threads/{thread_id}/decisions", response_model=list[DecisionOut])
def api_get_thread_decisions(thread_id: str):
    return get_decisions(thread_id)

# Activity APIs
@router.get("/activity", response_model=list[ActivityEventOut])
def api_get_all_activity():
    return get_activity_events()

@router.get("/activity/{object_type}/{object_id}", response_model=list[ActivityEventOut])
def api_get_object_activity(object_type: str, object_id: str):
    return get_activity_events(object_type, object_id)

# Notification APIs
@router.get("/notifications", response_model=list[NotificationOut])
def api_get_user_notifications():
    return get_notifications(mock_user_id)

@router.patch("/notifications/{notification_id}/read")
def api_mark_notification_read(notification_id: str):
    return mark_notification_read(notification_id)

@router.patch("/notifications/read-all")
def api_mark_all_notifications_read():
    return mark_all_read(mock_user_id)

# Review APIs
@router.post("/reviews", response_model=ReviewOut)
def api_request_review(review: ReviewCreate):
    # For demo, using review.status as reviewer_id parameter or we should just pass reviewer_id
    # Wait, ReviewCreate doesn't have reviewer_id, let's just use a hardcoded reviewer or assume comment has it.
    reviewer_id = "mock_reviewer" # In real app, it comes from request
    return request_review(review.object_type, review.object_id, reviewer_id, mock_user_id, review.workspace_id, review.project_id)

@router.get("/reviews/{object_type}/{object_id}", response_model=list[ReviewOut])
def api_get_object_reviews(object_type: str, object_id: str):
    return get_reviews(object_type, object_id)

@router.patch("/reviews/{review_id}")
def api_update_review(review_id: str, status: str, comment: str = None):
    return update_review_status(review_id, status, mock_user_id, comment)
