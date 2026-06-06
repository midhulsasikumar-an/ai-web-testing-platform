from __future__ import annotations

from backend.agent.planner.base_planner import BasePlanner, PlannerContext
from backend.agent.planner.exploration_planner import ExplorationPlanner
from backend.agent.planner.login_planner import LoginPlanner
from backend.agent.planner.regression_planner import RegressionPlanner
from backend.agent.services.auth_strategy_service import AuthStrategyService
from backend.core.models.planner import PlannerDecision


class PlannerOrchestrator:
    def __init__(self):
        self.auth_strategy_service = AuthStrategyService()
        self.planners: list[BasePlanner] = [
            LoginPlanner(),
            ExplorationPlanner(),
            RegressionPlanner(),
        ]

    def plan(self, context: PlannerContext) -> PlannerDecision:
        if context.auth_strategy is None:
            auth_strategy = self.auth_strategy_service.select_strategy(
                goal=context.goal,
                workflow_state=context.workflow_state,
                observation=context.observation,
                page_classification=context.page,
                auth_authenticated=context.auth.authenticated,
                credentials=context.credentials,
            )
            context = context.model_copy(update={"auth_strategy": auth_strategy})
        for planner in self.planners:
            if planner.can_handle(context):
                return planner.plan(context)
        return self.planners[-1].plan(context)


__all__ = [
    "BasePlanner",
    "PlannerContext",
    "PlannerOrchestrator",
    "LoginPlanner",
    "ExplorationPlanner",
    "RegressionPlanner",
]
