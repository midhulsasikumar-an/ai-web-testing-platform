from __future__ import annotations

from collections import Counter

from backend.core.models.auth import AuthRouteType
from backend.core.models.semantic_state import PageClassification

from backend.core.models.observations import Observation


class PageClassifier:
    def classify(self, observation: Observation) -> PageClassification:
        text = f"{observation.url} {observation.title} {' '.join(observation.headings)} {observation.page_text[:6000]}".lower()
        labels = " ".join(element.label.lower() for element in observation.elements if element.label)
        semantic_labels = " ".join(label.lower() for label in observation.semantic_labels)
        combined = f"{text} {labels} {semantic_labels}"

        score_map = Counter({
            "dashboard_home": 0.0,
            "admin_module": 0.0,
            "table_page": 0.0,
            "analytics_page": 0.0,
            "user_management": 0.0,
            "settings_page": 0.0,
            "form_page": 0.0,
            "modal_page": 0.0,
            "detail_page": 0.0,
            "listing_page": 0.0,
            "navigation_page": 0.0,
            "loading_page": 0.0,
            "empty_state_page": 0.0,
            "login_page": 0.0,
            "signup_page": 0.0,
            "oauth_page": 0.0,
            "forgot_password_page": 0.0,
            "landing_page": 0.0,
            "generic_page": 0.0,
        })
        signals: list[str] = []
        auth_scores = self._auth_scores(combined, observation)

        if any(term in combined for term in ["loading", "please wait", "spinner", "processing", "fetching"]):
            score_map["loading_page"] += 0.9
            signals.append("loading indicators detected")
        if observation.dialogs or any(term in combined for term in ["modal", "dialog", "popup", "overlay", "drawer"]):
            score_map["modal_page"] += 0.85
            signals.append("modal/dialog detected")
        if any(term in combined for term in ["login", "sign in", "log in", "password"]):
            score_map["login_page"] += 0.9
            signals.append("login/authentication language detected")
        if any(element.element_type == "password" for element in observation.inputs):
            score_map["login_page"] += 0.8
            signals.append("password input detected")
        if any(term in combined for term in ["sign up", "signup", "register", "create account", "join now", "get started"]):
            score_map["signup_page"] += 0.95
            signals.append("signup/register language detected")
        if any(term in combined for term in ["oauth", "google", "microsoft", "github", "apple", "single sign on", "sso", "continue with"]):
            score_map["oauth_page"] += 0.9
            signals.append("oauth/sso language detected")
        if any(term in combined for term in ["forgot password", "reset password", "recover password", "trouble signing in"]):
            score_map["forgot_password_page"] += 0.9
            signals.append("password recovery language detected")
        if any(term in combined for term in ["login", "sign in", "log in", "dashboard", "account", "enter your details", "access your account"]):
            score_map["landing_page"] += 0.1
        if any(term in combined for term in ["dashboard", "overview", "home", "welcome back"]):
            score_map["dashboard_home"] += 0.75
            signals.append("dashboard/home language detected")
        if any(term in combined for term in ["admin", "system users", "user management", "users", "permissions", "roles"]):
            score_map["admin_module"] += 0.8
            signals.append("admin/user management language detected")
            if any(term in combined for term in ["users", "system users", "user management", "manage users"]):
                score_map["user_management"] += 0.95
                signals.append("user management intent detected")
        if any(term in combined for term in ["settings", "preferences", "configuration", "profile settings"]):
            score_map["settings_page"] += 0.85
            signals.append("settings language detected")
        if observation.forms or len(observation.inputs) >= 2 or any(term in combined for term in ["form", "submit", "save changes", "create", "edit"]):
            score_map["form_page"] += 0.7
            signals.append("form controls detected")
        if any(term in combined for term in ["table", "grid", "rows", "columns", "pagination", "search", "filter", "sort"]):
            score_map["table_page"] += 0.75
            score_map["listing_page"] += 0.55
            signals.append("table/listing language detected")
        if any(term in combined for term in ["chart", "graph", "analytics", "metrics", "insights", "report"]):
            score_map["analytics_page"] += 0.9
            signals.append("analytics/reporting language detected")
        if any(term in combined for term in ["details", "detail view", "profile", "record details", "view"]):
            score_map["detail_page"] += 0.6
            signals.append("detail-view language detected")
        if any(term in combined for term in ["no records", "nothing to display", "empty state", "no results", "nothing found"]):
            score_map["empty_state_page"] += 0.95
            signals.append("empty state language detected")
        if len([element for element in observation.links if element.visible]) >= 12:
            score_map["navigation_page"] += 0.7
            signals.append("dense navigation detected")
        if len([element for element in observation.links if element.visible]) >= 6 and len([element for element in observation.buttons if element.visible]) >= 4:
            score_map["listing_page"] += 0.25
            signals.append("interactive listing detected")
        if any(term in combined for term in ["breadcrumb", "breadcrumb", "breadcrumbs"]) or len(observation.headings) > 1:
            score_map["detail_page"] += 0.15

        if max(score_map.values()) == 0:
            score_map["generic_page"] = 0.4
            signals.append("default generic classification")

        page_type, confidence = max(score_map.items(), key=lambda item: item[1])
        semantic_state = self._semantic_state(page_type, combined, observation)
        detected_modules = self._detected_modules(combined)
        return PageClassification(
            page_type=page_type,
            confidence=min(confidence, 0.99),
            signals=signals,
            semantic_state=semantic_state,
            detected_modules=detected_modules,
            route_type=self._auth_route_type(auth_scores, page_type),
            auth_scores=auth_scores,
        )

    @staticmethod
    def _semantic_state(page_type: str, combined: str, observation: Observation) -> str:
        if page_type == "dashboard_home":
            return "dashboard_home"
        if page_type in {"admin_module", "user_management"}:
            return page_type
        if page_type == "settings_page":
            return "settings_page"
        if page_type == "login_page":
            return "login_page"
        if page_type == "form_page":
            return "form_page"
        if page_type in {"table_page", "listing_page"}:
            return "listing_page"
        if page_type == "modal_page":
            return "modal_page"
        if page_type == "detail_page":
            return "detail_page"
        if any(term in combined for term in ["dashboard", "overview"]):
            return "dashboard_home"
        if any(term in combined for term in ["admin", "users"]):
            return "admin_module"
        if observation.forms:
            return "form_page"
        return page_type

    @staticmethod
    def _detected_modules(combined: str) -> list[str]:
        mapping = {
            "admin": "admin_module",
            "users": "user_management",
            "settings": "settings_page",
            "dashboard": "dashboard_home",
            "reports": "analytics_page",
            "analytics": "analytics_page",
            "profile": "profile_module",
        }
        modules = {module for term, module in mapping.items() if term in combined}
        return sorted(modules)

    @staticmethod
    def _auth_scores(combined: str, observation: Observation) -> dict[str, float]:
        scores = {
            "login": 0.0,
            "signup": 0.0,
            "oauth": 0.0,
            "forgot_password": 0.0,
            "dashboard": 0.0,
            "landing": 0.0,
        }
        if any(term in combined for term in ["login", "sign in", "log in", "continue"]):
            scores["login"] += 0.7
        if any(element.element_type == "password" for element in observation.inputs):
            scores["login"] += 0.25
        if any(term in combined for term in ["sign up", "signup", "register", "create account", "join now", "get started"]):
            scores["signup"] += 0.88
        if any(term in combined for term in ["oauth", "google", "microsoft", "github", "apple", "sso", "continue with"]):
            scores["oauth"] += 0.92
        if any(term in combined for term in ["forgot password", "reset password", "recover password", "trouble signing in"]):
            scores["forgot_password"] += 0.9
        if any(term in combined for term in ["dashboard", "home", "welcome back"]):
            scores["dashboard"] += 0.75
        if any(term in combined for term in ["login", "signup", "register", "join now", "get started", "welcome", "start"]):
            scores["landing"] += 0.4
        return scores

    @staticmethod
    def _auth_route_type(auth_scores: dict[str, float], fallback_page_type: str) -> str:
        best_key = max(auth_scores.items(), key=lambda item: item[1])[0] if auth_scores else "landing"
        if best_key == "login":
            return AuthRouteType.LOGIN_PAGE.value
        if best_key == "signup":
            return AuthRouteType.SIGNUP_PAGE.value
        if best_key == "oauth":
            return AuthRouteType.OAUTH_PAGE.value
        if best_key == "forgot_password":
            return AuthRouteType.FORGOT_PASSWORD_PAGE.value
        if best_key == "dashboard":
            return AuthRouteType.DASHBOARD_PAGE.value
        if best_key == "landing":
            return AuthRouteType.LANDING_PAGE.value
        return fallback_page_type
