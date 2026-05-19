from __future__ import annotations

"""
Agent run state, step, request/response models.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

from backend.core.models.actions import ActionResult, AgentAction, BrowserArtifact
from backend.core.models.memory import MemoryEvent
from backend.core.models.observations import Observation
from backend.core.models.planner import PlannerDecision
from backend.core.models.validation import ValidationResult
from backend.core.models.workflow import WorkflowState


class NavigationCandidate(BaseModel):
    """A candidate URL for frontier-based navigation."""
    url: str
    text: str = ""
    source_element_index: Optional[int] = None
    depth: int = 0
    score: float = 0.0
    reason: str = ""
    visited: bool = False
    discovery_step: int = 0
    parent_url: Optional[str] = None


class AgentStep(BaseModel):
    """A single step in the agent's execution trace."""
    step_number: int
    page_url: str = ""
    observation: Observation
    dom_summary: str = ""
    workflow_state_before: WorkflowState = WorkflowState.INIT
    workflow_state_after: WorkflowState = WorkflowState.INIT
    planner_decision: Optional[PlannerDecision] = None
    action: Optional[AgentAction] = None
    validation: Optional[ValidationResult] = None
    result: Optional[ActionResult] = None
    recovery_actions: List[ActionResult] = Field(default_factory=list)
    recovery_decision: Optional[Dict[str, Any]] = None
    observation_diff: Optional[Dict[str, Any]] = None
    navigation_transition: Optional[Dict[str, Any]] = None
    goal_evaluation: Optional[Dict[str, Any]] = None
    semantic_state: Optional[str] = None
    skill_used: Optional[str] = None
    reasoning_trace: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""
    duration_ms: int = 0
    trajectory_reward: float = 0.0
    token_usage: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRunState(BaseModel):
    """Complete state of an agent run."""
    run_id: str
    start_url: str
    goal: str
    objective_id: Optional[str] = None
    status: Literal[
        "running", "completed", "failed", "blocked",
        "cancelled", "max_steps_reached", "paused",
    ] = "running"
    current_url: str = ""
    workflow_state: WorkflowState = WorkflowState.INIT
    current_step: int = 0
    max_steps: int = 30
    max_retries_per_action: int = 2
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    steps: List[AgentStep] = Field(default_factory=list)
    memory_events: List[MemoryEvent] = Field(default_factory=list)
    artifacts: List[BrowserArtifact] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    trajectory_score: float = 0.0
    total_token_usage: int = 0
    skills_used: List[str] = Field(default_factory=list)
    failures_encountered: List[str] = Field(default_factory=list)


class AgentRunRequest(BaseModel):
    """Request to start an agent run."""
    url: HttpUrl
    goal: str
    credentials: Optional[Dict[str, str]] = None
    max_steps: int = Field(default=30, ge=1, le=200)
    same_origin_only: bool = True
    objective_decomposition: bool = True
    enable_vision: bool = True
    enable_memory: bool = True
    priority: int = Field(default=5, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)


class AgentRunResponse(BaseModel):
    """Response from an agent run."""
    success: bool
    run: AgentRunState
    reasoning_output: Optional[Dict[str, Any]] = None
