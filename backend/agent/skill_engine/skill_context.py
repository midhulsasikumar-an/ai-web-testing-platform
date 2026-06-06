from __future__ import annotations

"""
Skill context — shared context object passed to all skills during evaluation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.models.workflow import GoalType, WorkflowState
from backend.core.models.observations import Observation
from backend.core.models.actions import AgentAction
from backend.agent.services.auth_detector import AuthDetectionResult
from backend.agent.services.form_service import FormAnalysis
from backend.agent.services.page_classifier import PageClassification
from backend.core.models.auth import AuthenticationStrategyPlan


class SkillContext(BaseModel):
    """All contextual information a skill needs to evaluate applicability and plan actions."""
    goal: GoalType
    workflow_state: WorkflowState
    observation: Observation
    page_classification: PageClassification
    form_analysis: FormAnalysis
    auth_result: AuthDetectionResult
    auth_strategy: Optional[AuthenticationStrategyPlan] = None
    credentials: Optional[Dict[str, str]] = None
    visited_urls: List[str] = Field(default_factory=list)
    recent_failures: List[Dict[str, Any]] = Field(default_factory=list)
    memory_hints: Dict[str, Any] = Field(default_factory=dict)
    world_graph_summary: Dict[str, Any] = Field(default_factory=dict)
    step_number: int = 0
    max_steps: int = 30
    active_objective: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
