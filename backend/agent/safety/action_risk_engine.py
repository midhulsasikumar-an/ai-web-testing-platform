from __future__ import annotations

"""
Action risk engine — comprehensive risk assessment for every action,
with destructive action detection, domain policy enforcement,
and permission-based execution control.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from backend.core.models.actions import AgentAction
from backend.core.models.observations import Observation
from backend.core.models.planner import RiskAssessment
from backend.core.models.workflow import ActionType

logger = logging.getLogger("agent.safety.risk_engine")


class DomainPolicy:
    """Per-domain safety policies."""
    def __init__(self, domain: str, max_risk_score: float = 0.3, forbidden_actions: Optional[List[str]] = None):
        self.domain = domain
        self.max_risk_score = max_risk_score
        self.forbidden_actions = forbidden_actions or []


class ActionRiskEngine:
    """
    Comprehensive risk assessment engine for agent actions.
    Every action receives a risk score, safety level, and execution permission.
    """

    DESTRUCTIVE_TERMS = {
        "delete", "remove", "drop", "terminate", "shutdown", "destroy",
        "purge", "erase", "wipe", "clear all", "reset",
    }
    PAYMENT_TERMS = {
        "purchase", "buy", "pay", "checkout", "wire", "transfer",
        "subscribe", "order", "billing", "payment",
    }
    AUTH_TERMS = {
        "change password", "reset password", "logout all", "revoke",
        "disable account", "deactivate", "delete account",
    }
    ADMIN_TERMS = {
        "admin", "superadmin", "root", "manage users", "system settings",
        "configuration", "deploy", "migrate",
    }
    REDIRECT_SCHEMES = {"javascript", "data", "blob", "ftp"}

    def __init__(
        self,
        auto_execute_threshold: float = 0.3,
        confirmation_threshold: float = 0.7,
        block_threshold: float = 0.9,
    ) -> None:
        self._auto_threshold = auto_execute_threshold
        self._confirmation_threshold = confirmation_threshold
        self._block_threshold = block_threshold
        self._domain_policies: Dict[str, DomainPolicy] = {}
        self._action_log: List[Dict[str, Any]] = []

    def register_domain_policy(self, policy: DomainPolicy) -> None:
        self._domain_policies[policy.domain] = policy

    def assess(self, action: AgentAction, observation: Observation) -> RiskAssessment:
        """Assess the risk of executing an action."""
        risk_score = 0.0
        risk_factors: List[str] = []
        mitigations: List[str] = []

        surface = self._action_surface(action)

        # Destructive action detection
        for term in self.DESTRUCTIVE_TERMS:
            if term in surface:
                risk_score += 0.5
                risk_factors.append(f"Destructive term detected: {term}")

        # Payment detection
        for term in self.PAYMENT_TERMS:
            if term in surface:
                risk_score += 0.6
                risk_factors.append(f"Payment/financial term: {term}")

        # Auth-sensitive actions
        for term in self.AUTH_TERMS:
            if term in surface:
                risk_score += 0.4
                risk_factors.append(f"Auth-sensitive action: {term}")

        # Admin actions
        for term in self.ADMIN_TERMS:
            if term in surface:
                risk_score += 0.3
                risk_factors.append(f"Admin-level action: {term}")

        # External redirect detection
        if action.url:
            parsed = urlparse(action.url)
            if parsed.scheme in self.REDIRECT_SCHEMES:
                risk_score += 0.8
                risk_factors.append(f"Dangerous URL scheme: {parsed.scheme}")
            current_domain = urlparse(observation.url).netloc
            target_domain = parsed.netloc
            if target_domain and target_domain != current_domain:
                risk_score += 0.2
                risk_factors.append("Cross-domain navigation")

        # Low confidence amplifies risk
        if action.confidence < 0.5:
            risk_score += 0.15
            risk_factors.append("Low action confidence")

        # Domain policy check
        current_domain = urlparse(observation.url).netloc
        domain_policy = self._domain_policies.get(current_domain)
        if domain_policy:
            for forbidden in domain_policy.forbidden_actions:
                if forbidden in surface:
                    risk_score += 0.5
                    risk_factors.append(f"Domain policy violation: {forbidden}")

        risk_score = min(risk_score, 1.0)
        safety_level = self._safety_level(risk_score)
        requires_confirmation = risk_score >= self._confirmation_threshold
        destructive = any(t in surface for t in self.DESTRUCTIVE_TERMS)
        reversible = risk_score < 0.5

        if requires_confirmation:
            mitigations.append("Human confirmation required")
        if risk_score > 0.3:
            mitigations.append("Screenshot before and after execution")
        if destructive:
            mitigations.append("Verify action intent with replanning")

        assessment = RiskAssessment(
            risk_score=risk_score,
            safety_level=safety_level,
            destructive=destructive,
            reversible=reversible,
            requires_confirmation=requires_confirmation,
            risk_factors=risk_factors,
            mitigations=mitigations,
            rollback_possible=reversible,
        )

        self._action_log.append({
            "action": action.action.value,
            "target": action.target,
            "risk_score": risk_score,
            "safety_level": safety_level,
            "blocked": risk_score >= self._block_threshold,
        })

        return assessment

    def should_execute(self, assessment: RiskAssessment) -> bool:
        """Determine if the action should be auto-executed."""
        return assessment.risk_score < self._block_threshold

    def _safety_level(self, risk_score: float) -> str:
        if risk_score < self._auto_threshold:
            return "safe"
        if risk_score < self._confirmation_threshold:
            return "low_risk"
        if risk_score < self._block_threshold:
            return "high_risk"
        return "blocked"

    @staticmethod
    def _action_surface(action: AgentAction) -> str:
        return " ".join([
            action.action.value,
            action.target or "",
            action.reason or "",
            action.value or "",
            action.url or "",
        ]).lower()

    def get_risk_stats(self) -> Dict[str, Any]:
        if not self._action_log:
            return {"total": 0}
        total = len(self._action_log)
        blocked = sum(1 for a in self._action_log if a.get("blocked"))
        avg_risk = sum(a["risk_score"] for a in self._action_log) / total
        return {"total": total, "blocked": blocked, "avg_risk": round(avg_risk, 3)}
