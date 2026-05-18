from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

from backend.core.models.actions import AgentAction
from backend.core.models.workflow import FailureType
from backend.core.models.validation import ValidationResult


DANGEROUS_TERMS = {
    "delete",
    "remove",
    "drop",
    "terminate",
    "shutdown",
    "purchase",
    "buy",
    "pay",
    "checkout",
    "wire",
    "transfer",
    "change password",
    "reset password",
    "logout all",
}


@dataclass
class SafetyPolicy:
    start_url: str
    same_origin_only: bool = True
    allow_private_hosts: bool = False
    allowed_hosts: set[str] = field(default_factory=set)

    @classmethod
    def from_start_url(
        cls,
        start_url: str,
        same_origin_only: bool = True,
        allow_private_hosts: bool = False,
    ) -> "SafetyPolicy":
        parsed = urlparse(start_url)
        allowed_hosts = {parsed.netloc.lower()} if parsed.netloc else set()
        return cls(
            start_url=start_url,
            same_origin_only=same_origin_only,
            allow_private_hosts=allow_private_hosts,
            allowed_hosts=allowed_hosts,
        )

    def validate_start_url(self) -> ValidationResult:
        parsed = urlparse(self.start_url)
        if parsed.scheme not in {"http", "https"}:
            return ValidationResult(
                valid=False,
                reason="Only HTTP and HTTPS URLs are allowed",
                failure_type=FailureType.POLICY_BLOCKED,
            )
        if self._is_private_host(parsed.hostname or "") and not self.allow_private_hosts:
            return ValidationResult(
                valid=False,
                reason="Private or local network targets are blocked",
                failure_type=FailureType.POLICY_BLOCKED,
            )
        return ValidationResult(valid=True, reason="Start URL allowed")

    def validate_navigation(self, current_url: str, target_url: str) -> ValidationResult:
        normalized = urljoin(current_url, target_url)
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"}:
            return ValidationResult(
                valid=False,
                reason="Navigation scheme is not allowed",
                failure_type=FailureType.POLICY_BLOCKED,
            )
        if self._is_private_host(parsed.hostname or "") and not self.allow_private_hosts:
            return ValidationResult(
                valid=False,
                reason="Navigation to private or local network is blocked",
                failure_type=FailureType.POLICY_BLOCKED,
            )
        if self.same_origin_only and parsed.netloc.lower() not in self.allowed_hosts:
            return ValidationResult(
                valid=False,
                reason="Navigation outside allowed origin is blocked",
                failure_type=FailureType.POLICY_BLOCKED,
            )
        return ValidationResult(valid=True, reason="Navigation allowed")

    def validate_action(self, action: AgentAction, current_url: str) -> ValidationResult:
        surface = " ".join(
            [
                action.action.value,
                action.target or "",
                action.reason or "",
                action.value or "",
                action.url or "",
            ]
        ).lower()
        for term in DANGEROUS_TERMS:
            if term in surface:
                return ValidationResult(
                    valid=False,
                    reason=f"Potentially dangerous action blocked: {term}",
                    failure_type=FailureType.POLICY_BLOCKED,
                    policy_notes=["Destructive or financial actions require human approval."],
                )
        if action.url:
            return self.validate_navigation(current_url, action.url)
        return ValidationResult(valid=True, reason="Action allowed")

    def filter_urls(self, current_url: str, urls: Iterable[str]) -> List[str]:
        allowed: List[str] = []
        for url in urls:
            if self.validate_navigation(current_url, url).valid:
                allowed.append(urljoin(current_url, url))
        return allowed

    @staticmethod
    def _is_private_host(hostname: str) -> bool:
        if not hostname:
            return True
        lowered = hostname.lower()
        if lowered in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
            return True
        try:
            ip = ipaddress.ip_address(lowered)
        except ValueError:
            return False
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
