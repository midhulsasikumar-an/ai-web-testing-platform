from __future__ import annotations

"""
AI-agent style planner output models with reasoning traces,
candidate evaluation, skill selection, and risk assessment.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.models.workflow import GoalType, WorkflowState, FailureType
from backend.core.models.actions import AgentAction



class NavigationCandidate(BaseModel):
    url: str
    title: str = ""
    score: float = 0.0
    depth: int = 0
    visited: bool = False
    context: str = ""
class ReasoningStep(BaseModel):
    """A single step in the agent's reasoning chain."""
    step_index: int
    thought: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    alternatives_considered: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CandidateAction(BaseModel):
    """A candidate action evaluated but not necessarily selected."""
    action: AgentAction
    score: float = 0.0
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    selected: bool = False
    rejection_reason: Optional[str] = None


class RiskAssessment(BaseModel):
    """Risk evaluation for a proposed action or skill."""
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_level: str = "safe"
    destructive: bool = False
    reversible: bool = True
    requires_confirmation: bool = False
    risk_factors: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    rollback_possible: bool = True


class MemoryReference(BaseModel):
    """A reference to a memory record used in planning."""
    memory_type: str  # episodic, semantic, procedural
    reference_id: str
    relevance_score: float = 0.0
    content_summary: str = ""
    step_origin: Optional[int] = None


class SkillSelection(BaseModel):
    """The skill selected by the planner for execution."""
    skill_name: str
    applicability_score: float = 0.0
    preconditions_met: bool = True
    fallback_skills: List[str] = Field(default_factory=list)
    execution_strategy: str = "default"


class PlannerDecision(BaseModel):
    """
    Full planner output resembling modern AI-agent reasoning.

    This is the canonical planner output format that includes
    reasoning traces, candidate evaluation, skill selection,
    risk assessment, and memory references.
    """
    goal: GoalType
    workflow_state: WorkflowState
    objective: str = ""
    reasoning: List[str] = Field(default_factory=list)
    reasoning_trace: List[ReasoningStep] = Field(default_factory=list)
    candidate_actions: List[CandidateAction] = Field(default_factory=list)
    selected_skill: Optional[SkillSelection] = None
    risk_assessment: Optional[RiskAssessment] = None
    memory_references: List[MemoryReference] = Field(default_factory=list)
    next_action: AgentAction
    expected_outcome: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    completed: bool = False
    replan: bool = False
    planner_name: str = ""
    replanning_cause: Optional[str] = None
    trajectory_score: float = 0.0
    token_budget_used: int = 0
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class AgentReasoningOutput(BaseModel):
    """
    Top-level AI-agent style reasoning output.

    This is the format that external consumers and the orchestrator
    receive. It wraps PlannerDecision with additional context.
    """
    objective: str
    workflow_state: str
    candidate_actions: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_trace: List[Dict[str, Any]] = Field(default_factory=list)
    selected_skill: Optional[str] = None
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    memory_references: List[Dict[str, Any]] = Field(default_factory=list)
    next_action: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str = ""
    confidence: float = 0.0
    trajectory_score: float = 0.0

    @classmethod
    def from_decision(cls, decision: PlannerDecision) -> "AgentReasoningOutput":
        return cls(
            objective=decision.objective or decision.goal.value,
            workflow_state=decision.workflow_state.value,
            candidate_actions=[
                ca.model_dump(mode="json") for ca in decision.candidate_actions
            ],
            reasoning_trace=[
                rs.model_dump(mode="json") for rs in decision.reasoning_trace
            ],
            selected_skill=decision.selected_skill.skill_name if decision.selected_skill else None,
            risk_assessment=decision.risk_assessment.model_dump(mode="json") if decision.risk_assessment else {},
            memory_references=[
                mr.model_dump(mode="json") for mr in decision.memory_references
            ],
            next_action=decision.next_action.model_dump(mode="json"),
            expected_outcome=decision.expected_outcome,
            confidence=decision.confidence,
            trajectory_score=decision.trajectory_score,
        )
