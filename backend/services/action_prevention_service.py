from __future__ import annotations

from typing import Any, Dict

from backend.agent.memory_service import AgentMemory
from backend.core.models.actions import AgentAction
from backend.core.models.observations import Observation
from backend.core.models.workflow import FailureType


class ActionPreventionService:
    def semantic_retry_guard(self, action: AgentAction, observation: Observation, memory: AgentMemory) -> Dict[str, Any]:
        if memory.is_locked_target(action.url or "", action.target or "", action.selector or ""):
            return {
                "blocked": True,
                "reason": "Target route is already completed and locked",
                "failure_type": FailureType.STAGNATION,
                "risk_score": 0.96,
            }

        repeated_actions = memory.repeated_action_count(action)
        repeated_failures = memory.repeated_failure_count(action)
        if repeated_actions >= 2:
            return {
                "blocked": True,
                "reason": "The same action has already been attempted repeatedly",
                "failure_type": FailureType.STAGNATION,
                "risk_score": 0.9,
            }
        if repeated_failures >= 2:
            return {
                "blocked": True,
                "reason": "The same semantic target has failed repeatedly",
                "failure_type": FailureType.LOOP_DETECTED,
                "risk_score": 0.95,
            }

        if len(memory.observations) >= 3:
            last = memory.observations[-3:]
            if all(item.url == observation.url for item in last) and all(item.fingerprint == observation.fingerprint for item in last):
                return {
                    "blocked": True,
                    "reason": "Observation has not changed across multiple attempts",
                    "failure_type": FailureType.STAGNATION,
                    "risk_score": 0.88,
                }

        if len(memory.recent_action_keys) >= 3:
            recent = list(memory.recent_action_keys)[-3:]
            if len(set(recent)) == 1:
                return {
                    "blocked": True,
                    "reason": "Repeated planner reasoning would replay the same action",
                    "failure_type": FailureType.STAGNATION,
                    "risk_score": 0.9,
                }

        return {
            "blocked": False,
            "reason": "Action guard passed",
            "failure_type": FailureType.NONE,
            "risk_score": 0.0,
        }
