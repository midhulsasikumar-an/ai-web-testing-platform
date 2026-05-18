from __future__ import annotations

from typing import Any, Dict, Optional


class LiveReasoningEngine:
    """Deterministic narration generator for live execution streaming."""

    def narrate_observation(self, page_type: str, url: str, confidence: float, notes: Optional[str] = None) -> str:
        base = f"Detected {page_type.replace('_', ' ')} at {url}."
        if notes:
            base += f" {notes}"
        if confidence:
            base += f" Confidence {confidence:.2f}."
        return base

    def narrate_action(self, action: Dict[str, Any], reason: str = "") -> str:
        action_name = action.get("action", "action")
        target = action.get("target") or action.get("selector") or action.get("value") or ""
        message = f"Executing {action_name} {target}".strip()
        if reason:
            message += f" because {reason.lower()}"
        return message.rstrip(".") + "."

    def narrate_transition(self, from_state: str, to_state: str, summary: str = "") -> str:
        message = f"Workflow transitioned from {from_state.replace('_', ' ').lower()} to {to_state.replace('_', ' ').lower()}."
        if summary:
            message += f" {summary}"
        return message

    def narrate_issue(self, severity: str, message: str) -> str:
        return f"Detected {severity} issue: {message}."
