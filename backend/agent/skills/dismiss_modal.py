from __future__ import annotations

"""
Dismiss modal skill — detects and dismisses modals, overlays,
cookie banners, and dialog boxes blocking interaction.
"""

from typing import List, Optional

from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import ActionType


class DismissModalSkill(BaseSkill):
    name = "dismiss_modal"
    description = "Detect and dismiss modals, overlays, cookie banners, and dialogs"
    version = "2.0.0"
    priority = 98  # Very high — modals block everything
    tags = ["modal", "overlay", "dialog", "cookie"]

    DISMISS_LABELS = [
        "close", "cancel", "no thanks", "accept", "got it",
        "dismiss", "ok", "i understand", "continue", "skip",
        "not now", "later", "maybe later", "reject all",
        "accept all", "agree", "×", "x",
    ]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.observation.dialogs:
            score += 0.5
        if context.page_classification.page_type == "modal":
            score += 0.4
        obs = context.observation
        for el in obs.elements[:60]:
            label = el.label.lower()
            if any(term in label for term in self.DISMISS_LABELS):
                if el.role == "button" or el.tag == "button":
                    score += 0.15
                    break
        if any("modal" in (el.role or "").lower() for el in obs.elements[:60] if el.role):
            score += 0.2
        if any("overlay" in (el.element_id or "").lower() or "backdrop" in (el.element_id or "").lower()
               for el in obs.elements[:60]):
            score += 0.15
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        return True, "Modal detection is always available"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = ["Modal/overlay/dialog detected"]
        obs = context.observation

        if obs.dialogs:
            reasoning.append(f"Browser dialog present: {obs.dialogs[-1][:80]}")
            return SkillResult(
                action=AgentAction(
                    action=ActionType.KEYBOARD,
                    value="Escape",
                    confidence=0.85,
                    reason="Dismiss browser dialog via Escape",
                    expected_outcome="dialog dismissed",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=0.85,
                expected_outcome="dialog dismissed",
            )

        for el in obs.elements[:80]:
            label = el.label.lower()
            if (el.role == "button" or el.tag == "button") and el.visible and el.enabled:
                for dismiss_term in self.DISMISS_LABELS:
                    if dismiss_term in label:
                        reasoning.append(f"Found dismiss button: '{el.label}' at index {el.index}")
                        selector = el.selector_candidates[0].selector if el.selector_candidates else None
                        return SkillResult(
                            action=AgentAction(
                                action=ActionType.CLICK,
                                selector=selector,
                                element_index=el.index,
                                target=el.label,
                                confidence=0.88,
                                reason=f"Click dismiss button: {el.label}",
                                expected_outcome="modal/overlay dismissed",
                                skill_name=self.name,
                            ),
                            reasoning=reasoning,
                            confidence=0.88,
                            expected_outcome="modal dismissed, underlying content accessible",
                        )

        reasoning.append("No dismiss button found, attempting Escape key")
        return SkillResult(
            action=AgentAction(
                action=ActionType.KEYBOARD,
                value="Escape",
                confidence=0.7,
                reason="Attempt to dismiss modal via Escape key",
                expected_outcome="modal dismissed",
                skill_name=self.name,
            ),
            reasoning=reasoning,
            confidence=0.7,
            expected_outcome="modal dismissed via keyboard",
        )

    def expected_outcomes(self) -> List[str]:
        return ["modal dismissed", "overlay removed", "dialog closed", "cookie banner accepted"]
