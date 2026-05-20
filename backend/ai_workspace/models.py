from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ActiveContext(BaseModel):
    website: Optional[str] = None
    workflow: Optional[str] = None
    report: Optional[str] = None

class ChatSessionCreate(BaseModel):
    user_id: str = "demo-user"
    active_context: Optional[ActiveContext] = Field(default_factory=ActiveContext)

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    active_context: ActiveContext

class ChatMessage(BaseModel):
    session_id: str
    role: str # "user" or "assistant"
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retrieved_data: List[Dict[str, Any]] = []
    ai_summary: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: str = "demo-user"
    message: str
    context: Optional[ActiveContext] = None

class WorkflowGenerationRequest(BaseModel):
    user_id: str = "demo-user"
    prompt: str
