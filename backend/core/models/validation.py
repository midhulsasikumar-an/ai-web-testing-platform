"""
Validation result models.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from backend.core.models.workflow import FailureType


class ValidationResult(BaseModel):
    """Result of validating an action or policy check."""
    valid: bool
    reason: str = ""
    failure_type: FailureType = FailureType.NONE
    policy_notes: List[str] = Field(default_factory=list)


class ActionValidationResult(ValidationResult):
    """Extended validation result with risk scoring."""
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_level: str = "safe"
    requires_confirmation: bool = False
    suggested_alternatives: List[str] = Field(default_factory=list)
