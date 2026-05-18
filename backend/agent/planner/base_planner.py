from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from backend.agent.memory_service import AgentMemory
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import GoalType, WorkflowState
from backend.core.models.observations import Observation
from backend.core.models.planner import PlannerDecision
from backend.agent.services.auth_detector import AuthDetectionResult
from backend.agent.services.form_service import FormAnalysis
from backend.agent.services.frontier_service import FrontierService
from backend.agent.services.page_classifier import PageClassification
from backend.core.models.auth import AuthenticationStrategyPlan


class PlannerContext(BaseModel):
    goal: GoalType
    workflow_state: WorkflowState
    observation: Observation
    memory: AgentMemory
    page: PageClassification
    form: FormAnalysis
    auth: AuthDetectionResult
    auth_strategy: AuthenticationStrategyPlan | None = None
    frontier: FrontierService
    credentials: dict[str, str] | None = None

    class Config:
        arbitrary_types_allowed = True


class BasePlanner(ABC):
    name = "base"

    @abstractmethod
    def can_handle(self, context: PlannerContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def plan(self, context: PlannerContext) -> PlannerDecision:
        raise NotImplementedError

    def decision(
        self,
        context: PlannerContext,
        action: AgentAction,
        reasoning: list[str],
        completed: bool = False,
        replan: bool = False,
    ) -> PlannerDecision:
        return PlannerDecision(
            goal=context.goal,
            workflow_state=context.workflow_state,
            reasoning=reasoning,
            next_action=action,
            confidence=action.confidence,
            completed=completed,
            replan=replan,
            planner_name=self.name,
        )

    @staticmethod
    def selector_for(element) -> Optional[str]:
        if not element or not element.selector_candidates:
            return None
        return element.selector_candidates[0].selector
