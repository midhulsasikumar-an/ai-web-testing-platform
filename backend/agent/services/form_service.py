from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from backend.core.models.observations import ObservedElement, Observation


class ClassifiedField(BaseModel):
    element: ObservedElement
    semantic_type: str
    required: bool = False
    confidence: float = 0.0
    reason: str = ""


class FormAnalysis(BaseModel):
    fields: list[ClassifiedField] = Field(default_factory=list)
    submit_button: Optional[ObservedElement] = None
    confidence: float = 0.0
    signals: list[str] = Field(default_factory=list)

    def field(self, semantic_type: str) -> Optional[ClassifiedField]:
        matches = [item for item in self.fields if item.semantic_type == semantic_type]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.confidence, reverse=True)[0]


class FormIntelligenceService:
    def analyze(self, observation: Observation) -> FormAnalysis:
        fields = [self._classify_field(element) for element in observation.inputs]
        fields = [field for field in fields if field.semantic_type != "unknown"]
        submit_button = self.detect_submit_button(observation)
        signals: list[str] = []
        if any(field.semantic_type == "email" for field in fields):
            signals.append("email field identified")
        if any(field.semantic_type == "password" for field in fields):
            signals.append("password field identified")
        if submit_button:
            signals.append("submit button identified")
        confidence = min(0.35 + (len(signals) * 0.22), 0.99)
        return FormAnalysis(fields=fields, submit_button=submit_button, confidence=confidence, signals=signals)

    def detect_submit_button(self, observation: Observation) -> Optional[ObservedElement]:
        submit_terms = ["sign in", "login", "log in", "submit", "continue", "save", "create", "update"]
        candidates = []
        for element in observation.elements:
            label = element.label.lower()
            if element.role == "button" or element.tag == "button" or element.element_type == "submit":
                score = 0.4
                if element.element_type == "submit":
                    score += 0.3
                if any(term in label for term in submit_terms):
                    score += 0.4
                if element.visible and element.enabled:
                    score += 0.2
                candidates.append((score, element))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1] if candidates[0][0] >= 0.45 else None

    def _classify_field(self, element: ObservedElement) -> ClassifiedField:
        label = element.label.lower()
        element_type = (element.element_type or "").lower()
        semantic_type = "unknown"
        confidence = 0.0
        reason = ""

        if element_type == "password" or "password" in label:
            semantic_type = "password"
            confidence = 0.98
            reason = "password type or label"
        elif element_type == "email" or any(term in label for term in ["email", "e-mail", "mail"]):
            semantic_type = "email"
            confidence = 0.95
            reason = "email type or label"
        elif any(term in label for term in ["username", "user name", "login id", "userid"]):
            semantic_type = "username"
            confidence = 0.88
            reason = "username label"
        elif any(term in label for term in ["confirm password", "repeat password", "password confirmation"]):
            semantic_type = "confirm_password"
            confidence = 0.96
            reason = "confirm password label"
        elif any(term in label for term in ["search", "query"]):
            semantic_type = "search"
            confidence = 0.75
            reason = "search label"
        elif any(term in label for term in ["name", "title"]):
            semantic_type = "name"
            confidence = 0.65
            reason = "name/title label"
        elif any(term in label for term in ["first name", "firstname", "given name"]):
            semantic_type = "first_name"
            confidence = 0.82
            reason = "first name label"
        elif any(term in label for term in ["last name", "lastname", "surname"]):
            semantic_type = "last_name"
            confidence = 0.82
            reason = "last name label"

        return ClassifiedField(
            element=element,
            semantic_type=semantic_type,
            confidence=confidence,
            reason=reason,
        )
