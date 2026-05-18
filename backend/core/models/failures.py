"""
Failure taxonomy — structured failure types with severity,
recoverability, retry policies, and root cause tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.models.workflow import (
    FailureSeverity,
    FailureType,
    RecoverabilityLevel,
)


class RetryPolicy(BaseModel):
    """Policy governing how failures should be retried."""
    max_retries: int = 2
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    retry_on_failure_types: List[FailureType] = Field(default_factory=list)
    abort_on_failure_types: List[FailureType] = Field(
        default_factory=lambda: [FailureType.POLICY_BLOCKED, FailureType.BROWSER_CRASH]
    )
    cooldown_seconds: float = 0.0

    def should_retry(self, failure_type: FailureType, attempt: int) -> bool:
        if failure_type in self.abort_on_failure_types:
            return False
        if attempt >= self.max_retries:
            return False
        if self.retry_on_failure_types and failure_type not in self.retry_on_failure_types:
            return False
        return True

    def delay_for_attempt(self, attempt: int) -> float:
        return self.backoff_seconds * (self.backoff_multiplier ** attempt)


class AgentFailure(BaseModel):
    """Base failure model for all agent subsystem failures."""
    failure_id: str
    failure_type: FailureType
    severity: FailureSeverity
    recoverability: RecoverabilityLevel
    message: str
    root_cause: Optional[str] = None
    stack_trace: Optional[str] = None
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    context: Dict[str, Any] = Field(default_factory=dict)
    step: Optional[int] = None
    url: str = ""
    action_type: Optional[str] = None
    selector: Optional[str] = None
    recovery_suggestions: List[str] = Field(default_factory=list)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_strategy: Optional[str] = None

    def to_event_metadata(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "recoverability": self.recoverability.value,
            "message": self.message,
            "root_cause": self.root_cause,
            "url": self.url,
        }


class SelectorFailure(AgentFailure):
    """Failure when a DOM selector cannot be resolved."""
    failure_type: FailureType = FailureType.SELECTOR_NOT_FOUND
    severity: FailureSeverity = FailureSeverity.MEDIUM
    recoverability: RecoverabilityLevel = RecoverabilityLevel.RETRY_RECOVERABLE
    attempted_selectors: List[str] = Field(default_factory=list)
    element_index: Optional[int] = None
    target_label: Optional[str] = None
    dom_element_count: int = 0
    recovery_suggestions: List[str] = Field(
        default_factory=lambda: [
            "Re-observe the page to get fresh element indices",
            "Try alternative selector strategies",
            "Scroll to reveal hidden elements",
            "Check if element is inside an iframe",
        ]
    )


class AuthFailure(AgentFailure):
    """Failure during authentication workflow."""
    failure_type: FailureType = FailureType.AUTH_FAILURE
    severity: FailureSeverity = FailureSeverity.HIGH
    recoverability: RecoverabilityLevel = RecoverabilityLevel.REPLAN_REQUIRED
    auth_stage: str = ""  # credential_fill, form_submit, redirect, session_validation
    credentials_available: bool = False
    login_form_detected: bool = False
    error_message_on_page: Optional[str] = None
    recovery_suggestions: List[str] = Field(
        default_factory=lambda: [
            "Verify credentials are correct",
            "Check if CAPTCHA is blocking",
            "Look for alternative login methods",
            "Check for MFA requirements",
        ]
    )


class NavigationFailure(AgentFailure):
    """Failure during page navigation."""
    failure_type: FailureType = FailureType.NAVIGATION
    severity: FailureSeverity = FailureSeverity.MEDIUM
    recoverability: RecoverabilityLevel = RecoverabilityLevel.RETRY_RECOVERABLE
    source_url: str = ""
    target_url: str = ""
    http_status: Optional[int] = None
    redirect_chain: List[str] = Field(default_factory=list)
    recovery_suggestions: List[str] = Field(
        default_factory=lambda: [
            "Try navigating via browser back button",
            "Navigate to a known stable URL",
            "Refresh the current page",
            "Check if the target URL is valid",
        ]
    )


class TimeoutFailure(AgentFailure):
    """Failure due to action or page load timeout."""
    failure_type: FailureType = FailureType.TIMEOUT
    severity: FailureSeverity = FailureSeverity.MEDIUM
    recoverability: RecoverabilityLevel = RecoverabilityLevel.RETRY_RECOVERABLE
    timeout_ms: int = 0
    operation: str = ""  # page_load, element_wait, action_execution, network_idle
    recovery_suggestions: List[str] = Field(
        default_factory=lambda: [
            "Wait for network idle state",
            "Increase timeout threshold",
            "Check network connectivity",
            "Retry with domcontentloaded instead of networkidle",
        ]
    )


class RecoveryFailure(AgentFailure):
    """Failure during recovery/fallback execution."""
    failure_type: FailureType = FailureType.EXECUTION
    severity: FailureSeverity = FailureSeverity.HIGH
    recoverability: RecoverabilityLevel = RecoverabilityLevel.SKILL_SWITCH_REQUIRED
    original_failure_type: Optional[FailureType] = None
    recovery_strategy_attempted: str = ""
    recovery_attempts: int = 0
    recovery_suggestions: List[str] = Field(
        default_factory=lambda: [
            "Escalate to higher-level recovery",
            "Switch to alternative skill",
            "Reset workflow state",
            "Navigate to known safe state",
        ]
    )


class PlannerFailure(AgentFailure):
    """Failure in the planning/reasoning subsystem."""
    failure_type: FailureType = FailureType.LLM_PARSE_ERROR
    severity: FailureSeverity = FailureSeverity.HIGH
    recoverability: RecoverabilityLevel = RecoverabilityLevel.REPLAN_REQUIRED
    planner_name: str = ""
    input_context_size: int = 0
    raw_llm_output: Optional[str] = None
    recovery_suggestions: List[str] = Field(
        default_factory=lambda: [
            "Retry with simplified context",
            "Fall back to deterministic planner",
            "Reduce observation complexity",
            "Switch to a different skill",
        ]
    )
