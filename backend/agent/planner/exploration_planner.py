from __future__ import annotations

from backend.agent.planner.base_planner import BasePlanner, PlannerContext
from backend.core.models.workflow import ActionType, GoalType, WorkflowState
from backend.core.models.actions import AgentAction


class ExplorationPlanner(BasePlanner):
    name = "exploration_planner"

    def can_handle(self, context: PlannerContext) -> bool:
        return context.goal in {GoalType.EXPLORE_NAVIGATION, GoalType.NAVIGATE_DASHBOARD, GoalType.VALIDATE_UI}

    def plan(self, context: PlannerContext):
        goal_terms = [term for term in context.goal.value.split("_") if len(term) > 3]
        context.frontier.update(context.observation, goal_terms)
        candidate = context.frontier.next(context.memory.visited_urls)
        while candidate and context.memory.is_locked_target(candidate.url, candidate.text, ""):
            context.memory.mark_frontier_visited(candidate.url)
            candidate = context.frontier.next(context.memory.visited_urls)
        reasoning = [
            f"Workflow state is {context.workflow_state.value}",
            "Using graph frontier instead of ambiguous explore action",
        ]

        if candidate:
            reasoning.append(f"Selected frontier route with score {candidate.score:.1f}: {candidate.url}")
            action = AgentAction(
                goal=context.goal,
                workflow_state=context.workflow_state,
                action=ActionType.NAVIGATE,
                selector=None,
                element_index=candidate.source_element_index,
                target=candidate.text,
                url=candidate.url,
                confidence=min(max(candidate.score / 35, 0.66), 0.92),
                reason="Navigate to highest-ranked unexplored route",
                expected_outcome="new page state is observed",
            )
            return self.decision(context, action, reasoning)

        reasoning.append("No safe frontier route remains; scroll to discover more links")
        action = AgentAction(
            goal=context.goal,
            workflow_state=context.workflow_state,
            action=ActionType.SCROLL,
            value="800",
            confidence=0.66,
            reason="Reveal additional navigation candidates",
            expected_outcome="new navigation elements become visible",
        )
        return self.decision(context, action, reasoning, replan=True)
