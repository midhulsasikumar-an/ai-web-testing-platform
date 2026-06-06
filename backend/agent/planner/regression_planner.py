from __future__ import annotations

from backend.agent.planner.base_planner import BasePlanner, PlannerContext
from backend.core.models.workflow import ActionType, GoalType, WorkflowState
from backend.core.models.actions import AgentAction


class RegressionPlanner(BasePlanner):
    name = "regression_planner"

    def can_handle(self, context: PlannerContext) -> bool:
        return True

    def plan(self, context: PlannerContext):
        reasoning = [
            f"Fallback regression planner for goal {context.goal.value}",
            f"Page has {len(context.observation.elements)} interactive elements",
        ]
        if context.memory.detects_loop():
            action = AgentAction(
                goal=context.goal,
                workflow_state=WorkflowState.RECOVERY,
                action=ActionType.WAIT,
                confidence=0.5,
                reason="Loop risk detected; pause before recovery replanning",
                expected_outcome="page stabilizes for recovery",
            )
            return self.decision(context, action, reasoning, replan=True)

        clickable = [
            element
            for element in context.observation.elements
            if element.visible and element.enabled and element.role in {"button", "link", "tab", "menuitem"}
        ]
        if clickable:
            element = clickable[0]
            action = AgentAction(
                goal=context.goal,
                workflow_state=context.workflow_state,
                action=ActionType.CLICK,
                selector=self.selector_for(element),
                element_index=element.index,
                target=element.label,
                confidence=0.7,
                reason="Run deterministic UI regression click on first actionable control",
                expected_outcome="page responds without errors",
            )
            return self.decision(context, action, reasoning)

        action = AgentAction(
            goal=context.goal,
            workflow_state=context.workflow_state,
            action=ActionType.SCROLL,
            value="700",
            confidence=0.65,
            reason="No actionable control visible; scroll for additional content",
            expected_outcome="new actionable controls become visible",
        )
        return self.decision(context, action, reasoning, replan=True)
