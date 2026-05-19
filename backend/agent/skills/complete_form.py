from __future__ import annotations

"""
Complete form skill — intelligently fills and submits multi-field forms.
"""

from typing import List, Optional

from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.planner import RiskAssessment
from backend.core.models.workflow import ActionType, GoalType, WorkflowState


class CompleteFormSkill(BaseSkill):
    name = "complete_form"
    description = "Intelligently fill and submit multi-field forms"
    version = "2.0.0"
    priority = 80
    tags = ["form", "fill", "submit", "input"]

    DEFAULT_VALUES = {
        "name": "Test User",
        "email": "testuser@example.com",
        "phone": "+1234567890",
        "address": "123 Test Street",
        "city": "Test City",
        "zip": "12345",
        "search": "test query",
    }

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.goal == GoalType.SUBMIT_FORM:
            score += 0.4
        if context.page_classification.page_type == "form_page":
            score += 0.3
        if context.form_analysis.fields:
            score += min(len(context.form_analysis.fields) * 0.08, 0.3)
        if context.workflow_state == WorkflowState.FORM_INTERACTION:
            score += 0.2
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        if not context.form_analysis.fields and not context.observation.forms:
            return False, "No form fields detected on page"
        return True, "Form fields available"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = [f"Form analysis: {len(context.form_analysis.fields)} fields detected"]

        # Find the first unfilled field
        for field in context.form_analysis.fields:
            if field.element.value:
                continue
            if field.semantic_type in {"email", "username", "password"}:
                continue  # Handled by authenticate skill

            value = self._resolve_value(field.semantic_type, context)
            if not value:
                continue

            reasoning.append(f"Filling {field.semantic_type} field: '{field.element.label}'")
            selector = field.element.selector_candidates[0].selector if field.element.selector_candidates else None
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.FORM_INTERACTION,
                    action=ActionType.FILL,
                    selector=selector,
                    element_index=field.element.index,
                    target=field.element.label,
                    value=value,
                    confidence=field.confidence,
                    reason=f"Fill {field.semantic_type} field",
                    expected_outcome=f"{field.semantic_type} value entered",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=field.confidence,
                expected_outcome="form field populated",
            )

        # All fields filled — submit
        if context.form_analysis.submit_button:
            btn = context.form_analysis.submit_button
            reasoning.append("All fillable fields populated, submitting form")
            selector = btn.selector_candidates[0].selector if btn.selector_candidates else None
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.FORM_INTERACTION,
                    action=ActionType.SUBMIT,
                    selector=selector,
                    element_index=btn.index,
                    target=btn.label,
                    confidence=0.85,
                    reason="Submit completed form",
                    expected_outcome="form submitted successfully",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=0.85,
                expected_outcome="form submitted",
                risk=RiskAssessment(risk_score=0.2, safety_level="low_risk"),
            )

        reasoning.append("No actionable form fields or submit button found")
        return SkillResult(
            action=AgentAction(
                action=ActionType.SCROLL,
                value="500",
                confidence=0.55,
                reason="Scroll to reveal more form fields",
                skill_name=self.name,
            ),
            reasoning=reasoning,
            confidence=0.55,
            replan=True,
            expected_outcome="more form fields visible",
        )

    def _resolve_value(self, semantic_type: str, context: SkillContext) -> Optional[str]:
        creds = context.credentials or {}
        if semantic_type in creds:
            return creds[semantic_type]
        return self.DEFAULT_VALUES.get(semantic_type)

    def expected_outcomes(self) -> List[str]:
        return ["form field filled", "form submitted", "form validation passed"]
