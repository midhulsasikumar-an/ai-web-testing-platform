from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ExecutionEventType(str, Enum):
    AGENT_REASONING = "agent_reasoning"
    ACTION_EXECUTION = "action_execution"
    WORKFLOW_TRANSITION = "workflow_transition"
    BUG_DETECTED = "bug_detected"
    SCREENSHOT = "screenshot"
    ACCESSIBILITY_FINDING = "accessibility_finding"
    PERFORMANCE_FINDING = "performance_finding"
    TIMELINE_STEP = "timeline_step"
    RUN_STATUS = "run_status"
    REPLAY_EVENT = "replay_event"


class ExecutionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    agent: Optional[str] = None
    type: ExecutionEventType
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: int = 0
    workflow_state: Optional[str] = None
    action: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    url: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
