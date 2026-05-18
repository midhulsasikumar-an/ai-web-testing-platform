"""
Detect dashboard skill — validates successful navigation to dashboards.
Validate page skill — performs visual and structural page validation.
Pagination skill — handles paginated content navigation.
"""

from __future__ import annotations
from typing import List
from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import ActionType, GoalType, WorkflowState


class DetectDashboardSkill(BaseSkill):
    name = "detect_dashboard"
    description = "Validate successful navigation to dashboard/authenticated area"
    version = "2.0.0"
    priority = 60
    tags = ["dashboard", "validation", "authenticated"]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.goal == GoalType.NAVIGATE_DASHBOARD:
            score += 0.3
        if context.page_classification.page_type == "dashboard":
            score += 0.4
        if context.auth_result.authenticated:
            score += 0.2
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        if context.page_classification.page_type == "dashboard":
            return True, "Dashboard page detected"
        if context.auth_result.authenticated:
            return True, "Authenticated session"
        return False, "Not on dashboard and not authenticated"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning = [
            f"Page type: {context.page_classification.page_type}",
            f"Authenticated: {context.auth_result.authenticated}",
        ]
        if context.page_classification.page_type == "dashboard" and context.auth_result.authenticated:
            reasoning.append("Dashboard validated successfully")
            return SkillResult(
                action=AgentAction(
                    action=ActionType.WAIT, confidence=0.95,
                    reason="Dashboard reached and validated",
                    expected_outcome="dashboard state confirmed",
                    skill_name=self.name,
                ),
                reasoning=reasoning, confidence=0.95, completed=True,
                expected_outcome="dashboard validated",
            )
        reasoning.append("Dashboard not fully confirmed, exploring")
        return SkillResult(
            action=AgentAction(
                action=ActionType.SCROLL, value="400", confidence=0.65,
                reason="Explore dashboard content",
                expected_outcome="dashboard content revealed",
                skill_name=self.name,
            ),
            reasoning=reasoning, confidence=0.65,
            expected_outcome="more dashboard content visible",
        )

    def expected_outcomes(self) -> List[str]:
        return ["dashboard validated", "dashboard content explored"]


class ValidatePageSkill(BaseSkill):
    name = "validate_page"
    description = "Perform structural and visual page validation"
    version = "2.0.0"
    priority = 55
    tags = ["validation", "ui", "structure"]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.goal == GoalType.VALIDATE_UI:
            score += 0.4
        if context.workflow_state in {WorkflowState.TESTING, WorkflowState.EXPLORING}:
            score += 0.2
        if context.observation.console_errors:
            score += 0.15
        if context.observation.network_failures:
            score += 0.15
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        return True, "Page validation always available"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = []
        issues: List[str] = []
        obs = context.observation
        if obs.console_errors:
            issues.append(f"{len(obs.console_errors)} console errors")
        if obs.network_failures:
            issues.append(f"{len(obs.network_failures)} network failures")
        if not obs.headings:
            issues.append("no headings found")
        visible_count = sum(1 for el in obs.elements if el.visible)
        if visible_count < 3:
            issues.append("very few visible elements")
        if issues:
            reasoning.append(f"Page issues: {', '.join(issues)}")
        else:
            reasoning.append("Page structure appears valid")
        reasoning.append(f"Elements: {len(obs.elements)}, Visible: {visible_count}")

        return SkillResult(
            action=AgentAction(
                action=ActionType.SCROLL, value="600", confidence=0.7,
                reason="Validate page by scrolling through content",
                expected_outcome="full page content validated",
                skill_name=self.name,
                metadata={"validation_issues": issues},
            ),
            reasoning=reasoning, confidence=0.7,
            expected_outcome="page content validated",
        )

    def expected_outcomes(self) -> List[str]:
        return ["page validated", "issues detected", "structure confirmed"]


class PaginationSkill(BaseSkill):
    name = "pagination"
    description = "Navigate through paginated content"
    version = "2.0.0"
    priority = 50
    tags = ["pagination", "next", "previous", "page"]

    PAGINATION_TERMS = ["next", "previous", "prev", "page", "»", "›", "‹", "«", "load more", "show more"]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        for el in context.observation.elements[:100]:
            label = el.label.lower()
            if el.visible and any(t in label for t in self.PAGINATION_TERMS):
                score += 0.3
                break
        if context.goal in {GoalType.EXPLORE_NAVIGATION, GoalType.VALIDATE_UI}:
            score += 0.15
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        for el in context.observation.elements[:100]:
            if el.visible and any(t in el.label.lower() for t in self.PAGINATION_TERMS):
                return True, "Pagination controls found"
        return False, "No pagination controls found"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = ["Pagination controls detected"]
        for el in context.observation.elements[:100]:
            label = el.label.lower()
            if el.visible and el.enabled and any(t in label for t in ["next", "»", "›", "load more", "show more"]):
                reasoning.append(f"Found next/more button: '{el.label}'")
                selector = el.selector_candidates[0].selector if el.selector_candidates else None
                return SkillResult(
                    action=AgentAction(
                        action=ActionType.CLICK, selector=selector,
                        element_index=el.index, target=el.label,
                        confidence=0.8, reason=f"Navigate to next page: {el.label}",
                        expected_outcome="next page of content loaded",
                        skill_name=self.name,
                    ),
                    reasoning=reasoning, confidence=0.8,
                    expected_outcome="pagination advanced",
                )
        reasoning.append("No forward pagination found")
        return SkillResult(
            action=AgentAction(
                action=ActionType.SCROLL, value="800", confidence=0.55,
                reason="Scroll to find pagination controls",
                skill_name=self.name,
            ),
            reasoning=reasoning, confidence=0.55, replan=True,
            expected_outcome="pagination controls revealed",
        )

    def expected_outcomes(self) -> List[str]:
        return ["next page loaded", "more content loaded", "pagination navigated"]
