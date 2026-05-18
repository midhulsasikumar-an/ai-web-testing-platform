"""
Unified action models — agent actions, results, selector candidates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from backend.core.models.workflow import ActionType, FailureType, GoalType, WorkflowState


class SelectorCandidate(BaseModel):
    """A ranked candidate selector for targeting a DOM element."""
    selector: str
    strategy: Literal[
        "role", "data-testid", "aria-label", "id", "name",
        "placeholder", "text", "css", "xpath", "visual",
    ]
    score: float = 0.0
    reason: str = ""


class BoundingBox(BaseModel):
    """Screen-space bounding box for visual grounding."""
    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        return self.width * self.height


class ExpectedOutcome(BaseModel):
    """Structured expected outcome for post-action validation."""
    url_contains: Optional[str] = None
    text_contains: Optional[str] = None
    page_type: Optional[str] = None
    no_errors: bool = False
    element_visible_text: Optional[str] = None
    dom_fingerprint_changes: bool = False
    visual_change_expected: bool = False
    natural_language: Optional[str] = None


class AgentAction(BaseModel):
    """A single action the agent intends to perform."""
    goal: GoalType = GoalType.VALIDATE_UI
    workflow_state: WorkflowState = WorkflowState.INIT
    action: ActionType
    selector: Optional[str] = None
    element_index: Optional[int] = None
    target: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    expected_outcome: Optional[str] = None
    skill_name: Optional[str] = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BrowserArtifact(BaseModel):
    """An artifact captured during agent execution."""
    artifact_type: Literal[
        "screenshot", "trace", "dom", "console", "network",
        "video", "har", "accessibility_tree",
    ]
    path: Optional[str] = None
    label: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    size_bytes: int = 0
    content_hash: Optional[str] = None


class ActionResult(BaseModel):
    """Result of executing an agent action."""
    success: bool
    action: AgentAction
    failure_type: FailureType = FailureType.NONE
    error: Optional[str] = None
    selector_used: Optional[str] = None
    before_url: str = ""
    after_url: str = ""
    before_fingerprint: str = ""
    after_fingerprint: str = ""
    duration_ms: int = 0
    retries: int = 0
    artifacts: List[BrowserArtifact] = Field(default_factory=list)
    recovery_hint: Optional[str] = None
    visual_diff_score: float = 0.0
    dom_changes_detected: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
