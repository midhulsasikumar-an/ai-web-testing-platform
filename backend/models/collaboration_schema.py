from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

# Enums (as Literals for simplicity in Pydantic)
# Roles: owner, admin, editor, reviewer, viewer
# Object Types: bug, test_run, test_result, ai_report, recommendation, screenshot, project
# Review Statuses: pending, approved, changes_requested, dismissed

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceOut(WorkspaceBase):
    workspace_id: str
    created_by: str
    created_at: str
    updated_at: str

class ProjectBase(BaseModel):
    workspace_id: str
    name: str
    description: Optional[str] = ""

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    project_id: str
    created_by: str
    created_at: str
    updated_at: str

class WorkspaceMemberBase(BaseModel):
    workspace_id: str
    user_id: str
    role: str

class WorkspaceMemberCreate(WorkspaceMemberBase):
    pass

class WorkspaceMemberOut(WorkspaceMemberBase):
    membership_id: str
    created_at: str

class ThreadBase(BaseModel):
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    object_type: str
    object_id: str
    title: Optional[str] = None

class ThreadCreate(ThreadBase):
    pass

class ThreadOut(ThreadBase):
    thread_id: str
    created_by: str
    created_at: str
    updated_at: str
    comment_count: int
    last_activity_at: str

class CommentBase(BaseModel):
    thread_id: str
    body: str
    mentions: List[str] = []
    attachments: List[str] = []
    parent_comment_id: Optional[str] = None

class CommentCreate(BaseModel):
    body: str
    mentions: Optional[List[str]] = []
    attachments: Optional[List[str]] = []
    parent_comment_id: Optional[str] = None

class CommentOut(CommentBase):
    comment_id: str
    author_id: str
    is_decision: bool
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None

class DecisionBase(BaseModel):
    thread_id: str
    comment_id: str
    object_type: str
    object_id: str
    decision_text: str

class DecisionCreate(DecisionBase):
    pass

class DecisionOut(DecisionBase):
    decision_id: str
    created_by: str
    created_at: str

class ActivityEventBase(BaseModel):
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    event_type: str
    object_type: str
    object_id: str
    metadata: Dict[str, Any] = {}

class ActivityEventCreate(ActivityEventBase):
    pass

class ActivityEventOut(ActivityEventBase):
    event_id: str
    actor_id: str
    created_at: str

class NotificationBase(BaseModel):
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: str
    type: str
    object_type: str
    object_id: str
    title: str
    message: str

class NotificationCreate(NotificationBase):
    pass

class NotificationOut(NotificationBase):
    notification_id: str
    read: bool
    created_at: str

class ReviewBase(BaseModel):
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    object_type: str
    object_id: str
    status: str
    comment: Optional[str] = None

class ReviewCreate(BaseModel):
    object_type: str
    object_id: str
    status: str
    comment: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None

class ReviewOut(ReviewBase):
    review_id: str
    reviewer_id: str
    created_at: str
    updated_at: str
