"""
Skill router — routes execution to appropriate skills, manages
skill chains, and handles skill-level recovery.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillRegistry, SkillResult
from backend.agent.skill_engine.skill_selector import SkillSelector

logger = logging.getLogger("agent.skill_engine.router")


class SkillChain:
    """An ordered sequence of skills to execute as a workflow."""

    def __init__(self, name: str, skills: List[str], description: str = "") -> None:
        self.name = name
        self.skill_names = skills
        self.description = description
        self.current_index = 0
        self.results: List[SkillResult] = []
        self.completed = False

    @property
    def current_skill_name(self) -> Optional[str]:
        if self.current_index < len(self.skill_names):
            return self.skill_names[self.current_index]
        return None

    def advance(self) -> bool:
        self.current_index += 1
        if self.current_index >= len(self.skill_names):
            self.completed = True
            return False
        return True


class SkillRouter:
    """
    Routes execution requests to the appropriate skill(s).
    Manages skill chains and handles skill-level recovery by
    attempting fallbacks when a primary skill fails.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry
        self._selector = SkillSelector(registry)
        self._active_chains: Dict[str, SkillChain] = {}
        self._skill_execution_history: List[Dict] = []

    @property
    def selector(self) -> SkillSelector:
        return self._selector

    def route(self, context: SkillContext) -> Optional[SkillResult]:
        """Route to the best skill and return its planned action."""
        # Check if there's an active chain for the current objective
        chain = self._active_chains.get(context.active_objective or "")
        if chain and not chain.completed:
            return self._execute_chain_step(chain, context)

        selection = self._selector.select(context)
        if not selection:
            logger.warning("no_skill_routable", extra={"step": context.step_number})
            return None

        skill, score = selection
        try:
            result = skill.plan(context)
            self._record_execution(skill.name, context.step_number, True)
            return result
        except Exception as exc:
            logger.error(
                "skill_routing_error",
                extra={"skill": skill.name, "error": str(exc)},
            )
            return self._attempt_fallback(context, skill, str(exc))

    def create_chain(
        self,
        name: str,
        skill_names: List[str],
        objective: str = "",
    ) -> SkillChain:
        """Create a skill chain for multi-step workflows."""
        chain = SkillChain(name=name, skills=skill_names, description=objective)
        self._active_chains[objective or name] = chain
        logger.info(
            "skill_chain_created",
            extra={"name": name, "skills": skill_names, "objective": objective},
        )
        return chain

    def _execute_chain_step(
        self,
        chain: SkillChain,
        context: SkillContext,
    ) -> Optional[SkillResult]:
        """Execute the current step in a skill chain."""
        skill_name = chain.current_skill_name
        if not skill_name:
            chain.completed = True
            return None

        skill = self._registry.get(skill_name)
        if not skill:
            logger.warning("chain_skill_not_found", extra={"skill": skill_name})
            chain.advance()
            return self._execute_chain_step(chain, context)

        try:
            result = skill.plan(context)
            if result.completed:
                chain.results.append(result)
                chain.advance()
            return result
        except Exception as exc:
            logger.error(
                "chain_skill_error",
                extra={"skill": skill_name, "error": str(exc)},
            )
            chain.advance()
            return self._execute_chain_step(chain, context)

    def _attempt_fallback(
        self,
        context: SkillContext,
        failed_skill: BaseSkill,
        failure_reason: str,
    ) -> Optional[SkillResult]:
        """Attempt recovery via the failed skill's fallback or alternative skills."""
        fallback = failed_skill.recovery_fallback(context, failure_reason)
        if fallback:
            self._record_execution(f"{failed_skill.name}:fallback", context.step_number, True)
            return fallback

        candidates = self._selector.select_with_fallbacks(context, max_fallbacks=3)
        for skill, score in candidates[1:]:
            try:
                result = skill.plan(context)
                self._record_execution(skill.name, context.step_number, True)
                return result
            except Exception:
                continue

        self._record_execution(failed_skill.name, context.step_number, False)
        return None

    def _record_execution(self, skill_name: str, step: int, success: bool) -> None:
        self._skill_execution_history.append({
            "skill": skill_name,
            "step": step,
            "success": success,
        })

    def get_execution_stats(self) -> Dict[str, Dict[str, int]]:
        """Get per-skill execution statistics."""
        stats: Dict[str, Dict[str, int]] = {}
        for record in self._skill_execution_history:
            name = record["skill"]
            if name not in stats:
                stats[name] = {"total": 0, "success": 0, "failure": 0}
            stats[name]["total"] += 1
            if record["success"]:
                stats[name]["success"] += 1
            else:
                stats[name]["failure"] += 1
        return stats
