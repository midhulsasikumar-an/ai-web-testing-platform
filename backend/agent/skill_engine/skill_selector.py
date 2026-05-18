"""
Skill selector — selects the best skill for the current context,
evaluates candidates, and composes skill chains.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillRegistry, SkillResult
from backend.core.models.planner import CandidateAction, PlannerDecision, RiskAssessment, SkillSelection

logger = logging.getLogger("agent.skill_engine.selector")


class SkillSelector:
    """Selects the best skill based on context evaluation and confidence scoring."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def select(self, context: SkillContext) -> Optional[tuple[BaseSkill, float]]:
        """Select the single best skill for the current context."""
        candidates = self._registry.evaluate_all(context)
        if not candidates:
            logger.warning("no_applicable_skills", extra={"step": context.step_number})
            return None

        best_skill, best_score = candidates[0]
        logger.info(
            "skill_selected",
            extra={
                "skill": best_skill.name,
                "score": best_score,
                "candidates": len(candidates),
                "step": context.step_number,
            },
        )
        return best_skill, best_score

    def select_with_fallbacks(self, context: SkillContext, max_fallbacks: int = 3) -> List[tuple[BaseSkill, float]]:
        """Select primary skill plus fallback skills."""
        candidates = self._registry.evaluate_all(context)
        return candidates[: max_fallbacks + 1]

    def plan_with_skill(self, context: SkillContext) -> Optional[PlannerDecision]:
        """Full planning cycle: select skill, execute planning, return decision."""
        candidates = self._registry.evaluate_all(context)
        if not candidates:
            return None

        best_skill, best_score = candidates[0]
        try:
            result = best_skill.plan(context)
        except Exception as exc:
            logger.error("skill_plan_error", extra={"skill": best_skill.name, "error": str(exc)})
            # Try fallbacks
            for fallback_skill, fallback_score in candidates[1:]:
                try:
                    result = fallback_skill.plan(context)
                    best_skill = fallback_skill
                    best_score = fallback_score
                    break
                except Exception:
                    continue
            else:
                return None

        candidate_actions = [
            CandidateAction(
                action=result.action,
                score=best_score,
                pros=result.reasoning,
                selected=True,
            )
        ]
        for other_skill, other_score in candidates[1:4]:
            try:
                other_result = other_skill.plan(context)
                candidate_actions.append(
                    CandidateAction(
                        action=other_result.action,
                        score=other_score,
                        pros=other_result.reasoning,
                        selected=False,
                        rejection_reason=f"Lower applicability score ({other_score:.2f} vs {best_score:.2f})",
                    )
                )
            except Exception:
                continue

        fallback_names = [s.name for s, _ in candidates[1:4]]

        return PlannerDecision(
            goal=context.goal,
            workflow_state=context.workflow_state,
            objective=context.active_objective or context.goal.value,
            reasoning=result.reasoning,
            candidate_actions=candidate_actions,
            selected_skill=SkillSelection(
                skill_name=best_skill.name,
                applicability_score=best_score,
                preconditions_met=True,
                fallback_skills=fallback_names,
            ),
            risk_assessment=result.risk,
            next_action=result.action,
            expected_outcome=result.expected_outcome,
            confidence=result.confidence,
            completed=result.completed,
            replan=result.replan,
            planner_name=f"skill:{best_skill.name}",
        )
