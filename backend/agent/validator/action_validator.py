from __future__ import annotations

from urllib.parse import urljoin

from pydantic import BaseModel, Field

from backend.agent.memory_service import AgentMemory
from backend.agent.safety import SafetyPolicy
from backend.services.action_prevention_service import ActionPreventionService
from backend.core.models.workflow import ActionType
from backend.core.models.actions import AgentAction
from backend.core.models.workflow import FailureType
from backend.core.models.observations import Observation
from backend.core.models.validation import ValidationResult


class ActionValidationResult(ValidationResult):
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ActionValidationEngine:
    LOW_CONFIDENCE_REPLAN = 0.65
    LOW_CONFIDENCE_REJECT = 0.45

    def __init__(self, safety_policy: SafetyPolicy):
        self.safety_policy = safety_policy
        self.action_prevention = ActionPreventionService()

    def validate(self, action: AgentAction, observation: Observation, memory: AgentMemory) -> ActionValidationResult:
        policy = self.safety_policy.validate_action(action, observation.url)
        if not policy.valid:
            return ActionValidationResult(
                valid=False,
                reason=policy.reason,
                failure_type=policy.failure_type,
                risk_score=1.0,
                policy_notes=policy.policy_notes,
            )

        if action.confidence < self.LOW_CONFIDENCE_REJECT:
            return ActionValidationResult(
                valid=False,
                reason="Action confidence below execution threshold",
                failure_type=FailureType.INVALID_ACTION,
                risk_score=0.95,
            )

        risk_score = 0.0
        if action.confidence < self.LOW_CONFIDENCE_REPLAN:
            risk_score += 0.35

        retry_guard = self.action_prevention.semantic_retry_guard(action, observation, memory)
        if retry_guard["blocked"]:
            return ActionValidationResult(
                valid=False,
                reason=retry_guard["reason"],
                failure_type=retry_guard["failure_type"],
                risk_score=retry_guard["risk_score"],
            )

        if action.action == ActionType.WAIT:
            return ActionValidationResult(valid=True, reason="Wait action is safe", risk_score=risk_score)

        if action.action == ActionType.SCROLL:
            return ActionValidationResult(valid=True, reason="Scroll action is safe", risk_score=risk_score)

        if action.action == ActionType.BACK:
            if len(memory.visited_sequence) < 2:
                return ActionValidationResult(
                    valid=False,
                    reason="Back action has no previous navigation context",
                    failure_type=FailureType.INVALID_ACTION,
                    risk_score=0.7,
                )
            return ActionValidationResult(valid=True, reason="Back action has history", risk_score=risk_score)

        if action.action == ActionType.NAVIGATE:
            if not action.url:
                return ActionValidationResult(
                    valid=False,
                    reason="Navigate action requires URL",
                    failure_type=FailureType.INVALID_ACTION,
                    risk_score=0.8,
                )
            nav = self.safety_policy.validate_navigation(observation.url, urljoin(observation.url, action.url))
            return ActionValidationResult(
                valid=nav.valid,
                reason=nav.reason,
                failure_type=nav.failure_type,
                risk_score=risk_score if nav.valid else 1.0,
                policy_notes=nav.policy_notes,
            )

        element = self._resolve_element(action, observation)
        if element is None:
            return ActionValidationResult(
                valid=False,
                reason="Target element does not exist in observation",
                failure_type=FailureType.SELECTOR_NOT_FOUND,
                risk_score=0.85,
            )
        if action.selector and action.selector not in [candidate.selector for candidate in element.selector_candidates]:
            risk_score += 0.25
        if not element.visible:
            return ActionValidationResult(
                valid=False,
                reason="Target element is not visible",
                failure_type=FailureType.SELECTOR_NOT_FOUND,
                risk_score=0.8,
            )
        if not element.enabled:
            return ActionValidationResult(
                valid=False,
                reason="Target element is disabled",
                failure_type=FailureType.INVALID_ACTION,
                risk_score=0.9,
            )
        if action.action == ActionType.FILL and not element.editable:
            return ActionValidationResult(
                valid=False,
                reason="Fill action requires editable element",
                failure_type=FailureType.INVALID_ACTION,
                risk_score=0.9,
            )
        if action.action in {ActionType.CLICK, ActionType.SUBMIT, ActionType.HOVER, ActionType.SELECT, ActionType.FILL}:
            return ActionValidationResult(
                valid=True,
                reason="Element action is valid",
                risk_score=min(risk_score, 1.0),
            )

        return ActionValidationResult(
            valid=False,
            reason=f"Unsupported deterministic action: {action.action.value}",
            failure_type=FailureType.INVALID_ACTION,
            risk_score=1.0,
        )

    @staticmethod
    def _resolve_element(action: AgentAction, observation: Observation):
        if action.element_index is not None:
            return next((element for element in observation.elements if element.index == action.element_index), None)
        if action.selector:
            return next(
                (
                    element
                    for element in observation.elements
                    if any(candidate.selector == action.selector for candidate in element.selector_candidates)
                ),
                None,
            )
        if action.target:
            target = action.target.lower()
            return next((element for element in observation.elements if target in element.label.lower()), None)
        return None


def validate_action(
    action_data: AgentAction,
    observation: Observation,
    memory: AgentMemory,
    safety_policy: SafetyPolicy | None = None,
) -> ActionValidationResult:
    engine = ActionValidationEngine(safety_policy or SafetyPolicy.from_start_url(observation.url))
    return engine.validate(action_data, observation, memory)
