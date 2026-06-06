from __future__ import annotations

"""
Recover navigation skill — handles navigation failures, dead ends,
and returns the agent to a known-good state.
"""

from typing import List
from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import ActionType, WorkflowState


class RecoverNavigationSkill(BaseSkill):
    name = "recover_navigation"
    description = "Recover from navigation failures and dead-end states"
    version = "2.0.0"
    priority = 92
    tags = ["recovery", "navigation", "error", "dead-end"]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.workflow_state in {WorkflowState.ERROR, WorkflowState.RECOVERY}:
            score += 0.5
        if context.page_classification.page_type == "error_page":
            score += 0.4
        if context.recent_failures:
            score += min(len(context.recent_failures) * 0.1, 0.3)
        wg = context.world_graph_summary
        if wg.get("dead_ends", 0) > 0 or wg.get("stagnation_risk"):
            score += 0.2
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        return True, "Recovery always available"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = [
            f"State: {context.workflow_state.value}",
            f"Recent failures: {len(context.recent_failures)}",
        ]
        if context.page_classification.page_type == "error_page":
            reasoning.append("On error page — attempting browser back")
            return SkillResult(
                action=AgentAction(
                    action=ActionType.BACK, confidence=0.8,
                    reason="Navigate back from error page",
                    expected_outcome="return to previous working state",
                    skill_name=self.name,
                ),
                reasoning=reasoning, confidence=0.8,
                expected_outcome="returned to previous page",
            )
        if len(context.visited_urls) >= 2:
            reasoning.append("Attempting browser back to previous known state")
            return SkillResult(
                action=AgentAction(
                    action=ActionType.BACK, confidence=0.75,
                    reason="Navigate back to recover from failure",
                    expected_outcome="return to known-good state",
                    skill_name=self.name,
                ),
                reasoning=reasoning, confidence=0.75,
                expected_outcome="navigation recovered",
            )
        reasoning.append("No recovery path — waiting for stability")
        return SkillResult(
            action=AgentAction(
                action=ActionType.WAIT, confidence=0.5,
                reason="Wait for page stability during recovery",
                skill_name=self.name,
            ),
            reasoning=reasoning, confidence=0.5, replan=True,
            expected_outcome="page stabilized",
        )

    def expected_outcomes(self) -> List[str]:
        return ["navigation recovered", "returned to known state", "error page escaped"]
