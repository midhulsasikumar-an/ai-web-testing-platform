"""
Resolve overlay skill — handles cookie banners, notification popups,
and other overlays that partially block the page.
"""

from __future__ import annotations
from typing import List
from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import ActionType


class ResolveOverlaySkill(BaseSkill):
    name = "resolve_overlay"
    description = "Handle cookie banners, notification popups, and partial overlays"
    version = "2.0.0"
    priority = 96
    tags = ["overlay", "cookie", "banner", "notification"]

    COOKIE_TERMS = ["cookie", "privacy", "consent", "gdpr", "accept all", "reject all"]
    NOTIFICATION_TERMS = ["notification", "subscribe", "newsletter", "allow", "block"]

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        text = context.observation.page_text[:2000].lower()
        labels = " ".join(el.label.lower() for el in context.observation.elements[:60])
        if any(t in text or t in labels for t in self.COOKIE_TERMS):
            score += 0.45
        if any(t in text or t in labels for t in self.NOTIFICATION_TERMS):
            score += 0.3
        if context.observation.popups:
            score += 0.35
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        return True, "Overlay resolution always available"

    def plan(self, context: SkillContext) -> SkillResult:
        reasoning: List[str] = ["Overlay/banner detected"]
        for el in context.observation.elements[:80]:
            label = el.label.lower()
            if not (el.visible and el.enabled):
                continue
            if (el.role == "button" or el.tag == "button"):
                if any(t in label for t in ["accept all", "accept", "agree", "got it", "ok", "close", "dismiss"]):
                    reasoning.append(f"Found overlay dismiss: '{el.label}'")
                    selector = el.selector_candidates[0].selector if el.selector_candidates else None
                    return SkillResult(
                        action=AgentAction(
                            action=ActionType.CLICK, selector=selector,
                            element_index=el.index, target=el.label,
                            confidence=0.88, reason=f"Dismiss overlay: {el.label}",
                            expected_outcome="overlay removed", skill_name=self.name,
                        ),
                        reasoning=reasoning, confidence=0.88,
                        expected_outcome="overlay dismissed",
                    )
        reasoning.append("No dismiss button found, trying Escape")
        return SkillResult(
            action=AgentAction(
                action=ActionType.KEYBOARD, value="Escape",
                confidence=0.65, reason="Dismiss overlay via Escape",
                skill_name=self.name,
            ),
            reasoning=reasoning, confidence=0.65,
            expected_outcome="overlay dismissed via keyboard",
        )

    def expected_outcomes(self) -> List[str]:
        return ["cookie banner dismissed", "notification popup closed", "overlay removed"]
