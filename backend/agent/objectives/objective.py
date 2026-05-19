from __future__ import annotations

"""
Objective-driven execution system — hierarchical task decomposition,
subtask management, dependency graphs, and completion scoring.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ObjectiveStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class SuccessCriteria(BaseModel):
    """Defines what constitutes successful completion of an objective."""
    criteria_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    description: str
    check_type: str = "text_contains"  # text_contains, url_contains, page_type, element_visible, custom
    expected_value: str = ""
    weight: float = 1.0
    met: bool = False
    evidence: Optional[str] = None

    def evaluate(self, observation_data: Dict[str, Any]) -> bool:
        text = f"{observation_data.get('url', '')} {observation_data.get('title', '')} {observation_data.get('page_text', '')}".lower()
        if self.check_type == "text_contains":
            self.met = self.expected_value.lower() in text
        elif self.check_type == "url_contains":
            self.met = self.expected_value.lower() in observation_data.get("url", "").lower()
        elif self.check_type == "page_type":
            self.met = observation_data.get("page_type", "") == self.expected_value
        elif self.check_type == "element_visible":
            elements = observation_data.get("elements", [])
            self.met = any(self.expected_value.lower() in str(e).lower() for e in elements)
        if self.met:
            self.evidence = f"Criteria '{self.description}' met via {self.check_type}"
        return self.met


class Constraint(BaseModel):
    """Execution constraint for an objective."""
    constraint_type: str  # max_steps, timeout, required_state, forbidden_action
    value: Any
    description: str = ""
    enforced: bool = True


class Subtask(BaseModel):
    """A subtask within a larger objective."""
    subtask_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str
    description: str = ""
    parent_id: Optional[str] = None
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    priority: int = 5
    dependencies: List[str] = Field(default_factory=list)  # subtask_ids
    success_criteria: List[SuccessCriteria] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    assigned_skill: Optional[str] = None
    max_attempts: int = 3
    attempts: int = 0
    completion_score: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def can_start(self, completed_subtasks: set[str]) -> bool:
        return all(dep in completed_subtasks for dep in self.dependencies)

    def evaluate_completion(self, observation_data: Dict[str, Any]) -> float:
        if not self.success_criteria:
            return 0.0
        total_weight = sum(c.weight for c in self.success_criteria)
        met_weight = sum(c.weight for c in self.success_criteria if c.evaluate(observation_data))
        self.completion_score = met_weight / total_weight if total_weight > 0 else 0.0
        if self.completion_score >= 1.0:
            self.status = ObjectiveStatus.COMPLETED
            self.completed_at = datetime.utcnow()
        return self.completion_score

    def mark_failed(self, reason: str) -> None:
        self.status = ObjectiveStatus.FAILED
        self.failure_reason = reason
        self.completed_at = datetime.utcnow()


class Objective(BaseModel):
    """Top-level objective with hierarchical subtask decomposition."""
    objective_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:16])
    name: str
    description: str = ""
    goal_type: str = "custom"
    subtasks: List[Subtask] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    priority: int = 5
    completion_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_subtask(self, subtask: Subtask) -> None:
        subtask.parent_id = self.objective_id
        self.subtasks.append(subtask)

    def get_next_subtask(self) -> Optional[Subtask]:
        completed_ids = {s.subtask_id for s in self.subtasks if s.status == ObjectiveStatus.COMPLETED}
        for subtask in sorted(self.subtasks, key=lambda s: s.priority, reverse=True):
            if subtask.status == ObjectiveStatus.PENDING and subtask.can_start(completed_ids):
                return subtask
        return None

    def evaluate_completion(self, observation_data: Dict[str, Any]) -> float:
        if not self.subtasks:
            return 0.0
        for subtask in self.subtasks:
            if subtask.status in {ObjectiveStatus.PENDING, ObjectiveStatus.IN_PROGRESS}:
                subtask.evaluate_completion(observation_data)
        completed = sum(1 for s in self.subtasks if s.status == ObjectiveStatus.COMPLETED)
        self.completion_score = completed / len(self.subtasks)
        if self.completion_score >= 1.0:
            self.status = ObjectiveStatus.COMPLETED
            self.completed_at = datetime.utcnow()
        return self.completion_score

    def propagate_failure(self, failed_subtask_id: str) -> List[str]:
        """Mark dependent subtasks as blocked when a subtask fails."""
        blocked: List[str] = []
        for subtask in self.subtasks:
            if failed_subtask_id in subtask.dependencies and subtask.status == ObjectiveStatus.PENDING:
                subtask.status = ObjectiveStatus.BLOCKED
                subtask.failure_reason = f"Blocked by failed dependency: {failed_subtask_id}"
                blocked.append(subtask.subtask_id)
        return blocked


class ExecutionPlan(BaseModel):
    """An execution plan decomposing a high-level goal into objectives."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    goal: str
    objectives: List[Objective] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_active_objective(self) -> Optional[Objective]:
        for obj in sorted(self.objectives, key=lambda o: o.priority, reverse=True):
            if obj.status in {ObjectiveStatus.PENDING, ObjectiveStatus.IN_PROGRESS}:
                return obj
        return None

    @classmethod
    def decompose_goal(cls, goal: str) -> "ExecutionPlan":
        """Decompose a high-level goal into a structured execution plan."""
        plan = cls(goal=goal)
        normalized = goal.lower().replace("-", "_").replace(" ", "_")

        if any(t in normalized for t in ["login", "auth", "sign_in"]):
            obj = Objective(name="authenticate_user", goal_type="authenticate_user")
            obj.add_subtask(Subtask(
                name="navigate_to_login", assigned_skill="navigate_sidebar",
                success_criteria=[SuccessCriteria(description="Login page visible", check_type="page_type", expected_value="login_page")],
            ))
            obj.add_subtask(Subtask(
                name="fill_credentials", assigned_skill="authenticate",
                dependencies=[obj.subtasks[-1].subtask_id] if obj.subtasks else [],
                success_criteria=[SuccessCriteria(description="Credentials entered", check_type="text_contains", expected_value="password")],
            ))
            obj.add_subtask(Subtask(
                name="submit_login", assigned_skill="authenticate",
                dependencies=[obj.subtasks[-1].subtask_id] if obj.subtasks else [],
                success_criteria=[SuccessCriteria(description="Dashboard reached", check_type="page_type", expected_value="dashboard")],
            ))
            plan.objectives.append(obj)

        elif any(t in normalized for t in ["dashboard", "navigate", "explore"]):
            obj = Objective(name="explore_application", goal_type="explore_navigation")
            obj.add_subtask(Subtask(name="explore_main_navigation", assigned_skill="navigate_sidebar"))
            obj.add_subtask(Subtask(name="validate_pages", assigned_skill="validate_page"))
            plan.objectives.append(obj)

        elif any(t in normalized for t in ["form", "submit"]):
            obj = Objective(name="complete_form_workflow", goal_type="submit_form")
            obj.add_subtask(Subtask(name="locate_form", assigned_skill="navigate_sidebar"))
            obj.add_subtask(Subtask(name="fill_form_fields", assigned_skill="complete_form"))
            obj.add_subtask(Subtask(name="submit_form", assigned_skill="complete_form"))
            plan.objectives.append(obj)

        else:
            obj = Objective(name="general_validation", goal_type="validate_ui")
            obj.add_subtask(Subtask(name="explore_and_validate", assigned_skill="validate_page"))
            plan.objectives.append(obj)

        return plan
