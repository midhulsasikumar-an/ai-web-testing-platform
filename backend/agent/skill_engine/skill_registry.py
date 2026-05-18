"""
Skill registry — central registry for all agent skills with
metadata, versioning, and dynamic discovery.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from backend.agent.skill_engine.skill_context import SkillContext
from backend.core.models.actions import AgentAction
from backend.core.models.planner import PlannerDecision, RiskAssessment, SkillSelection

logger = logging.getLogger("agent.skill_engine.registry")


class SkillResult:
    """Result of skill evaluation or execution."""
    def __init__(
        self,
        action: AgentAction,
        reasoning: List[str],
        confidence: float = 0.0,
        completed: bool = False,
        replan: bool = False,
        expected_outcome: str = "",
        risk: Optional[RiskAssessment] = None,
    ):
        self.action = action
        self.reasoning = reasoning
        self.confidence = confidence
        self.completed = completed
        self.replan = replan
        self.expected_outcome = expected_outcome
        self.risk = risk or RiskAssessment()


class BaseSkill:
    """
    Abstract base class for all agent skills.

    Every skill must implement:
    - name: unique identifier
    - description: human-readable description
    - applicability_score: how applicable is this skill to the current context
    - check_preconditions: whether preconditions for this skill are met
    - plan: produce the next action for this skill
    - recovery_fallback: what to do if the skill fails
    """
    name: str = "base_skill"
    description: str = ""
    version: str = "1.0.0"
    priority: int = 50  # higher = evaluated first
    tags: List[str] = []

    def applicability_score(self, context: SkillContext) -> float:
        """Score from 0.0 to 1.0 indicating how applicable this skill is."""
        return 0.0

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        """Check if all preconditions are met. Returns (met, reason)."""
        return True, "No preconditions"

    def plan(self, context: SkillContext) -> SkillResult:
        """Produce the next action for this skill."""
        raise NotImplementedError

    def recovery_fallback(self, context: SkillContext, failure_reason: str) -> Optional[SkillResult]:
        """Provide a fallback action when this skill fails."""
        return None

    def expected_outcomes(self) -> List[str]:
        """List of outcomes this skill can produce."""
        return []


class SkillRegistry:
    """
    Central registry managing all available agent skills.

    Skills are registered at startup and queried dynamically
    during planning based on context applicability.
    """

    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill
        self._skill_classes[skill.name] = type(skill)
        logger.info("skill_registered", extra={"name": skill.name, "version": skill.version})

    def unregister(self, name: str) -> None:
        self._skills.pop(name, None)
        self._skill_classes.pop(name, None)

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def all_skills(self) -> List[BaseSkill]:
        return sorted(self._skills.values(), key=lambda s: s.priority, reverse=True)

    def evaluate_all(self, context: SkillContext) -> List[tuple[BaseSkill, float]]:
        """Evaluate all skills and return sorted by applicability score."""
        scored: List[tuple[BaseSkill, float]] = []
        for skill in self._skills.values():
            try:
                score = skill.applicability_score(context)
                if score > 0.0:
                    preconditions_met, reason = skill.check_preconditions(context)
                    if preconditions_met:
                        scored.append((skill, score))
                    else:
                        logger.debug(
                            "skill_precondition_failed",
                            extra={"skill": skill.name, "reason": reason},
                        )
            except Exception as exc:
                logger.warning(
                    "skill_evaluation_error",
                    extra={"skill": skill.name, "error": str(exc)},
                )
        return sorted(scored, key=lambda item: item[1], reverse=True)

    @property
    def count(self) -> int:
        return len(self._skills)

    def list_skills(self) -> List[Dict[str, str]]:
        return [
            {"name": s.name, "description": s.description, "version": s.version}
            for s in self._skills.values()
        ]
