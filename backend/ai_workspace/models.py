from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActiveContext(BaseModel):
    website: Optional[str] = None
    workflow: Optional[str] = None
    report: Optional[str] = None
    test_run_id: Optional[str] = None
    bug_id: Optional[str] = None
    screenshot_path: Optional[str] = None


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    active_context: Optional[ActiveContext] = Field(default_factory=ActiveContext)


class ChatSession(BaseModel):
    session_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    active_context: ActiveContext = Field(default_factory=ActiveContext)


class ChatSessionRename(BaseModel):
    title: str


class ChatMessage(BaseModel):
    session_id: str
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retrieved_data: List[Dict[str, Any]] = Field(default_factory=list)
    ai_summary: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    context: Optional[ActiveContext] = None


class MemoryCreate(BaseModel):
    memory_type: str
    content: str
    importance: int = Field(default=50, ge=1, le=100)


class MemoryUpdate(BaseModel):
    memory_type: Optional[str] = None
    content: Optional[str] = None
    importance: Optional[int] = Field(default=None, ge=1, le=100)


class ReportAnalysisRequest(BaseModel):
    report_id: Optional[str] = None
    query: Optional[str] = None


class BugAnalysisRequest(BaseModel):
    query: Optional[str] = None


class ScreenshotAnalysisRequest(BaseModel):
    report_id: Optional[str] = None
    test_run_id: Optional[str] = None
    screenshot_path: Optional[str] = None


class InstructionGenerationRequest(BaseModel):
    topic: str
