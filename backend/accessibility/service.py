from __future__ import annotations

from typing import Any, Dict, List

from backend.core.models.observations import Observation


class AccessibilityAuditService:
    """Deterministic accessibility heuristics over semantic observations."""

    def audit(self, observation: Observation) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        for element in observation.inputs:
            label = element.label.strip()
            if not label and not element.placeholder and not element.name and element.element_type not in {"hidden", "submit"}:
                findings.append({
                    "type": "missing_label",
                    "severity": "high",
                    "element_index": element.index,
                    "description": "Form control lacks an accessible name or label.",
                })
            aria = element.aria_label.strip().lower()
            if aria and any(term in aria for term in ["null", "undefined", "false"]):
                findings.append({
                    "type": "invalid_aria",
                    "severity": "medium",
                    "element_index": element.index,
                    "description": "ARIA label appears invalid or placeholder-like.",
                })
        if observation.forms and not observation.inputs:
            findings.append({
                "type": "inaccessible_form",
                "severity": "high",
                "description": "Form detected without accessible input controls.",
            })
        if any(term in observation.page_text.lower() for term in ["press tab", "keyboard only", "skip to content"]):
            findings.append({
                "type": "keyboard_navigation_risk",
                "severity": "medium",
                "description": "Page copy suggests keyboard-only workflow guidance; verify tab order and focus visibility.",
            })
        if any(term in observation.page_text.lower() for term in ["contrast", "low contrast", "hard to read"]):
            findings.append({
                "type": "contrast_problem",
                "severity": "medium",
                "description": "Visual text suggests a potential contrast accessibility issue.",
            })
        if any(term in observation.page_text.lower() for term in ["modal", "dialog", "overlay"]) and not any("close" in element.label.lower() for element in observation.buttons):
            findings.append({
                "type": "focus_trap_risk",
                "severity": "high",
                "description": "Modal or overlay detected without an obvious close control.",
            })
        score = max(0, 100 - len(findings) * 12)
        return {
            "accessibility_score": score,
            "findings": findings,
            "keyboard_navigation_risk": any(item["type"] == "keyboard_navigation_risk" for item in findings),
            "focus_trap_risk": any(item["type"] == "focus_trap_risk" for item in findings),
        }
