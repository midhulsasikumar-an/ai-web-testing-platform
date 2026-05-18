"""
Search site skill — performs search operations on web applications.
"""

from __future__ import annotations

from typing import List

from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import ActionType, GoalType


class SearchSiteSkill(BaseSkill):
    name = "search_site"
    description = "Find and use search functionality on web applications"
    version = "2.0.0"
    priority = 65
    tags = ["search", "query", "find"]

    SEARCH_INDICATORS = ["search", "query", "find", "lookup", "filter"]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.goal == GoalType.TEST_SEARCH:
            score += 0.5
        search_field = context.form_analysis.field("search")
        if search_field:
            score += 0.35
        for el in context.observation.elements[:80]:
            label = el.label.lower()
            if el.editable and any(t in label for t in self.SEARCH_INDICATORS):
                score += 0.2
                break
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        search_field = context.form_analysis.field("search")
        if search_field:
            return True, "Search field detected"
        for el in context.observation.elements[:80]:
            if el.editable and any(t in el.label.lower() for t in self.SEARCH_INDICATORS):
                return True, "Search input found"
        return False, "No search input found on page"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = ["Search functionality detected"]
        search_field = context.form_analysis.field("search")

        if search_field and not search_field.element.value:
            selector = search_field.element.selector_candidates[0].selector if search_field.element.selector_candidates else None
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    action=ActionType.FILL,
                    selector=selector,
                    element_index=search_field.element.index,
                    target=search_field.element.label,
                    value="test",
                    confidence=0.8,
                    reason="Enter search query",
                    expected_outcome="search results displayed",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=0.8,
                expected_outcome="search query entered",
            )

        # Search might be filled — look for search button
        for el in context.observation.elements[:80]:
            label = el.label.lower()
            if (el.role == "button" or el.tag == "button") and el.visible:
                if any(t in label for t in self.SEARCH_INDICATORS):
                    selector = el.selector_candidates[0].selector if el.selector_candidates else None
                    reasoning.append(f"Search button found: '{el.label}'")
                    return SkillResult(
                        action=AgentAction(
                            goal=context.goal,
                            action=ActionType.CLICK,
                            selector=selector,
                            element_index=el.index,
                            target=el.label,
                            confidence=0.82,
                            reason="Click search button",
                            expected_outcome="search results displayed",
                            skill_name=self.name,
                        ),
                        reasoning=reasoning,
                        confidence=0.82,
                        expected_outcome="search executed",
                    )

        # Fallback: submit via Enter key
        reasoning.append("No search button found, submitting via keyboard")
        return SkillResult(
            action=AgentAction(
                action=ActionType.KEYBOARD,
                value="Enter",
                confidence=0.7,
                reason="Submit search via Enter key",
                expected_outcome="search results displayed",
                skill_name=self.name,
            ),
            reasoning=reasoning,
            confidence=0.7,
            expected_outcome="search submitted",
        )

    def expected_outcomes(self) -> List[str]:
        return ["search query entered", "search results displayed", "search executed"]
