"""
Navigate sidebar skill — discovers and navigates sidebar/menu navigation elements.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urljoin

from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import ActionType, GoalType


class NavigateSidebarSkill(BaseSkill):
    name = "navigate_sidebar"
    description = "Discover and navigate sidebar/menu navigation elements"
    version = "2.0.0"
    priority = 70
    tags = ["navigation", "sidebar", "menu"]

    NAV_ROLES = {"link", "menuitem", "tab", "treeitem"}
    NAV_TAGS = {"a", "nav"}

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.goal in {GoalType.EXPLORE_NAVIGATION, GoalType.NAVIGATE_DASHBOARD, GoalType.VALIDATE_UI}:
            score += 0.3
        if context.workflow_state.value in {"DASHBOARD", "AUTHENTICATED", "TESTING", "EXPLORING"}:
            score += 0.2
        nav_links = self._find_nav_links(context)
        unvisited = [l for l in nav_links if l.href and l.href not in context.visited_urls]
        if unvisited:
            score += min(len(unvisited) * 0.05, 0.4)
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        nav_links = self._find_nav_links(context)
        if not nav_links:
            return False, "No navigation links found"
        return True, f"Found {len(nav_links)} navigation links"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = [f"Workflow: {context.workflow_state.value}"]
        nav_links = self._find_nav_links(context)
        unvisited = [
            el for el in nav_links
            if el.href and urljoin(context.observation.url, el.href) not in context.visited_urls
        ]

        if not unvisited:
            reasoning.append("All navigation links already visited")
            return SkillResult(
                action=AgentAction(
                    action=ActionType.SCROLL,
                    value="800",
                    confidence=0.6,
                    reason="All sidebar links visited, scrolling for more",
                    expected_outcome="new navigation elements revealed",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=0.6,
                replan=True,
                expected_outcome="more navigation options found",
            )

        # Score and select the best candidate
        best = self._score_candidates(unvisited, context)
        target_url = urljoin(context.observation.url, best.href) if best.href else ""
        reasoning.append(f"Selected nav link: '{best.label}' -> {target_url}")
        selector = best.selector_candidates[0].selector if best.selector_candidates else None

        return SkillResult(
            action=AgentAction(
                goal=context.goal,
                workflow_state=context.workflow_state,
                action=ActionType.CLICK,
                selector=selector,
                element_index=best.index,
                target=best.label,
                url=target_url,
                confidence=0.82,
                reason=f"Navigate to '{best.label}'",
                expected_outcome="new page state observed",
                skill_name=self.name,
            ),
            reasoning=reasoning,
            confidence=0.82,
            expected_outcome=f"navigated to {best.label}",
        )

    def _find_nav_links(self, context: SkillContext):
        return [
            el for el in context.observation.elements[:120]
            if (el.role in self.NAV_ROLES or el.tag in self.NAV_TAGS)
            and el.visible and el.enabled and el.href
        ]

    def _score_candidates(self, candidates, context: SkillContext):
        goal_terms = [t for t in context.goal.value.split("_") if len(t) > 3]
        scored = []
        for el in candidates:
            s = 10.0
            label = el.label.lower()
            for term in goal_terms:
                if term in label:
                    s += 8
            if any(t in label for t in ["dashboard", "settings", "profile", "reports", "admin"]):
                s += 6
            if any(t in label for t in ["logout", "delete", "privacy", "terms"]):
                s -= 20
            scored.append((s, el))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def expected_outcomes(self) -> List[str]:
        return ["navigated to new page", "sidebar link clicked", "menu item selected"]
