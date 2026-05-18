from __future__ import annotations

from pydantic import BaseModel, Field
from playwright.async_api import BrowserContext

from backend.core.models.observations import Observation


class AuthDetectionResult(BaseModel):
    authenticated: bool
    confidence: float
    signals: list[str] = Field(default_factory=list)


class AuthDetector:
    async def detect(self, observation: Observation, context: BrowserContext | None = None) -> AuthDetectionResult:
        score = 0.0
        signals: list[str] = []
        combined = f"{observation.url} {observation.title} {observation.page_text[:3000]}".lower()
        labels = " ".join(element.label.lower() for element in observation.elements)

        if any(term in combined for term in ["dashboard", "account", "profile", "admin", "settings"]):
            score += 0.28
            signals.append("authenticated route or content pattern")
        if any(term in labels for term in ["logout", "sign out", "my account", "profile", "avatar"]):
            score += 0.36
            signals.append("logout/profile controls present")
        if observation.page_type in {"dashboard", "dashboard_home", "dashboard_page"}:
            score += 0.25
            signals.append("classified as dashboard")
        if "login" not in observation.url.lower() and not any(element.element_type == "password" for element in observation.inputs):
            score += 0.1
            signals.append("not currently on login form")

        if context is not None:
            try:
                cookies = await context.cookies()
                auth_cookies = [
                    cookie
                    for cookie in cookies
                    if any(term in cookie.get("name", "").lower() for term in ["session", "auth", "token", "jwt"])
                ]
                if auth_cookies:
                    score += 0.3
                    signals.append("auth/session cookie present")
            except Exception:
                pass

        confidence = min(score, 0.99)
        return AuthDetectionResult(
            authenticated=confidence >= 0.65,
            confidence=confidence,
            signals=signals,
        )
