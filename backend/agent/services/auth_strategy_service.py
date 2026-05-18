from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.core.models.auth import (
    AuthRouteClassification,
    AuthRouteType,
    AuthenticationMode,
    AuthenticationStrategy,
    AuthenticationStrategyCandidate,
    AuthenticationStrategyPlan,
)
from backend.core.models.observations import Observation
from backend.core.models.semantic_state import PageClassification
from backend.core.models.workflow import GoalType, WorkflowState
from backend.config.agent_config import get_config


@dataclass
class _StrategyScore:
    strategy: AuthenticationStrategy
    score: float
    reason: str
    locked: bool = False


class AuthStrategyService:
    def classify_route(self, observation: Observation, page_classification: PageClassification) -> AuthRouteClassification:
        text = f"{observation.url} {observation.title} {' '.join(observation.headings)} {observation.page_text[:6000]}".lower()
        labels = " ".join(element.label.lower() for element in observation.elements)
        combined = f"{text} {labels} {page_classification.route_type}".lower()

        route_scores = {
            AuthRouteType.LOGIN_PAGE.value: self._login_score(combined, observation),
            AuthRouteType.SIGNUP_PAGE.value: self._signup_score(combined, observation),
            AuthRouteType.OAUTH_PAGE.value: self._oauth_score(combined),
            AuthRouteType.FORGOT_PASSWORD_PAGE.value: self._forgot_password_score(combined),
            AuthRouteType.DASHBOARD_PAGE.value: self._dashboard_score(combined, observation),
            AuthRouteType.LANDING_PAGE.value: self._landing_score(combined),
        }
        route_type = max(route_scores.items(), key=lambda item: item[1])[0]
        confidence = min(max(route_scores.values()), 0.99)
        signals = self._route_signals(route_type, route_scores)
        return AuthRouteClassification(
            route_type=AuthRouteType(route_type),
            confidence=confidence,
            login_score=route_scores[AuthRouteType.LOGIN_PAGE.value],
            signup_score=route_scores[AuthRouteType.SIGNUP_PAGE.value],
            oauth_score=route_scores[AuthRouteType.OAUTH_PAGE.value],
            forgot_password_score=route_scores[AuthRouteType.FORGOT_PASSWORD_PAGE.value],
            dashboard_score=route_scores[AuthRouteType.DASHBOARD_PAGE.value],
            landing_score=route_scores[AuthRouteType.LANDING_PAGE.value],
            signals=signals,
        )

    def select_strategy(
        self,
        goal: GoalType,
        workflow_state: WorkflowState,
        observation: Observation,
        page_classification: PageClassification,
        auth_authenticated: bool,
        credentials: Optional[Dict[str, str]] = None,
        auth_required: Optional[bool] = None,
    ) -> AuthenticationStrategyPlan:
        config = get_config()
        route = self.classify_route(observation, page_classification)
        credentials_provided = bool(credentials and any(credentials.get(key) for key in ["email", "username", "user", "password"]))
        requires_auth = self._auth_required(goal, workflow_state, observation, page_classification, auth_required)

        if auth_authenticated:
            return AuthenticationStrategyPlan(
                strategy=AuthenticationStrategy.GUEST_ACCESS,
                mode=AuthenticationMode.SKIP_AUTH_MODE,
                route=route,
                confidence=0.99,
                candidates=[
                    AuthenticationStrategyCandidate(
                        strategy=AuthenticationStrategy.GUEST_ACCESS,
                        confidence=0.99,
                        reason="Session already authenticated; skip auth",
                        locked=True,
                    )
                ],
                locked=True,
                lock_reason="Already authenticated",
                credentials_provided=credentials_provided,
                auth_required=requires_auth,
                reasoning=["Authentication already active; bypass authentication flow."],
            )

        # Enforce login priority for critical goals when credentials exist
        if credentials_provided and goal in {GoalType.RUN_REGRESSION, GoalType.AUTHENTICATE_USER, GoalType.EXPLORE_NAVIGATION}:
            return AuthenticationStrategyPlan(
                strategy=AuthenticationStrategy.LOGIN_EXISTING_USER,
                mode=AuthenticationMode.LOGIN_PRIORITY_MODE,
                route=route,
                confidence=0.99,
                candidates=[
                    AuthenticationStrategyCandidate(
                        strategy=AuthenticationStrategy.LOGIN_EXISTING_USER,
                        confidence=0.99,
                        reason="Credentials provided and high-priority goal; enforce login-first",
                        locked=True,
                    )
                ],
                locked=True,
                lock_reason="Login-priority enforced by policy",
                credentials_provided=credentials_provided,
                auth_required=requires_auth,
                reasoning=["Credentials present; enforcing login-first strategy for regression/auth tests."],
            )

        scores = self._score_strategies(credentials_provided, requires_auth, route, page_classification, observation)
        ordered = sorted(scores, key=lambda item: item.score, reverse=True)
        chosen = ordered[0]
        mode = self._mode_for_strategy(chosen.strategy)
        lock_reason = self._lock_reason(chosen.strategy, credentials_provided, route)
        # Enforce signup policy: only allow account creation if config allows it or explicit signup goal
        if chosen.strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
            if not get_config().allow_account_creation and not (goal == GoalType.AUTHENTICATE_USER and route.route_type == AuthRouteType.SIGNUP_PAGE):
                # downgrade to guest or login depending on credentials
                fallback = AuthenticationStrategy.LOGIN_EXISTING_USER if credentials_provided else AuthenticationStrategy.GUEST_ACCESS
                fallback_score = 0.85 if credentials_provided else 0.7
                return AuthenticationStrategyPlan(
                    strategy=fallback,
                    mode=self._mode_for_strategy(fallback),
                    route=route,
                    confidence=fallback_score,
                    candidates=[AuthenticationStrategyCandidate(strategy=fallback, confidence=fallback_score, reason="Account creation disabled by config; performing validation-only or guest flow", locked=True)],
                    locked=True,
                    lock_reason="Account creation disabled",
                    credentials_provided=credentials_provided,
                    auth_required=requires_auth,
                    reasoning=["Account creation disabled by configuration; downgrade strategy"],
                )
        return AuthenticationStrategyPlan(
            strategy=chosen.strategy,
            mode=mode,
            route=route,
            confidence=chosen.score,
            candidates=[
                AuthenticationStrategyCandidate(strategy=item.strategy, confidence=item.score, reason=item.reason, locked=item.locked)
                for item in ordered
            ],
            locked=chosen.strategy in {AuthenticationStrategy.LOGIN_EXISTING_USER, AuthenticationStrategy.CREATE_NEW_ACCOUNT},
            lock_reason=lock_reason,
            credentials_provided=credentials_provided,
            auth_required=requires_auth,
            reasoning=self._reasoning(chosen.strategy, credentials_provided, requires_auth, route),
        )

    @staticmethod
    def _score_strategies(
        credentials_provided: bool,
        requires_auth: bool,
        route: AuthRouteClassification,
        page_classification: PageClassification,
        observation: Observation,
    ) -> List[_StrategyScore]:
        route_type = route.route_type.value if hasattr(route.route_type, "value") else str(route.route_type)
        login_score = route.login_score
        signup_score = route.signup_score
        oauth_score = route.oauth_score
        landing_score = route.landing_score

        if credentials_provided:
            login_score += 0.35
            signup_score -= 0.5
            oauth_score += 0.05
            if route_type == AuthRouteType.LOGIN_PAGE.value:
                login_score += 0.25
            if route_type == AuthRouteType.SIGNUP_PAGE.value:
                signup_score -= 0.2
            if any(term in observation.title.lower() for term in ["login", "sign in"]):
                login_score += 0.15
            if any(term in observation.page_text.lower() for term in ["create account", "register"]):
                signup_score -= 0.15
        else:
            if requires_auth:
                signup_score += 0.35
                oauth_score += 0.15
            else:
                landing_score += 0.45

        if route_type == AuthRouteType.OAUTH_PAGE.value:
            oauth_score += 0.45
        if route_type == AuthRouteType.SIGNUP_PAGE.value:
            signup_score += 0.45
        if route_type == AuthRouteType.LOGIN_PAGE.value:
            login_score += 0.45
        if route_type == AuthRouteType.DASHBOARD_PAGE.value:
            login_score += 0.25
            landing_score += 0.15

        if page_classification.page_type in {"dashboard_home", "admin_module", "user_management"}:
            login_score += 0.2

        scores = [
            _StrategyScore(AuthenticationStrategy.LOGIN_EXISTING_USER, login_score, "Credentials and login semantics rank highest" if credentials_provided else "Login route detected"),
            _StrategyScore(AuthenticationStrategy.CREATE_NEW_ACCOUNT, signup_score, "No credentials and authentication required" if requires_auth and not credentials_provided else "Signup route detected"),
            _StrategyScore(AuthenticationStrategy.OAUTH_LOGIN, oauth_score, "OAuth route or provider controls detected"),
            _StrategyScore(AuthenticationStrategy.GUEST_ACCESS, landing_score, "Guest flow available or auth not required"),
        ]

        if not requires_auth:
            scores.append(_StrategyScore(AuthenticationStrategy.GUEST_ACCESS, max(landing_score, 0.75), "Workflow can continue without authentication", locked=True))
        return scores

    @staticmethod
    def _auth_required(goal: GoalType, workflow_state: WorkflowState, observation: Observation, page_classification: PageClassification, auth_required: Optional[bool]) -> bool:
        if auth_required is not None:
            return auth_required
        if workflow_state in {WorkflowState.LOGIN_PAGE, WorkflowState.SIGNUP_PAGE, WorkflowState.AUTHENTICATED, WorkflowState.DASHBOARD, WorkflowState.DASHBOARD_HOME, WorkflowState.ADMIN_MODULE, WorkflowState.USER_MANAGEMENT}:
            return True
        goal_value = goal.value if hasattr(goal, "value") else str(goal)
        if any(term in goal_value for term in ["auth", "login", "register", "signup", "dashboard", "admin", "user", "settings"]):
            return True
        route_type = page_classification.route_type
        if route_type in {AuthRouteType.LOGIN_PAGE.value, AuthRouteType.SIGNUP_PAGE.value, AuthRouteType.OAUTH_PAGE.value, AuthRouteType.FORGOT_PASSWORD_PAGE.value}:
            return True
        text = f"{observation.title} {' '.join(observation.headings)} {observation.page_text}".lower()
        return any(term in text for term in ["login", "sign in", "register", "create account", "dashboard", "admin", "profile", "settings"])

    @staticmethod
    def _mode_for_strategy(strategy: AuthenticationStrategy) -> AuthenticationMode:
        if strategy == AuthenticationStrategy.LOGIN_EXISTING_USER:
            return AuthenticationMode.LOGIN_PRIORITY_MODE
        if strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
            return AuthenticationMode.ACCOUNT_CREATION_MODE
        if strategy == AuthenticationStrategy.GUEST_ACCESS:
            return AuthenticationMode.GUEST_MODE
        return AuthenticationMode.GUEST_MODE

    @staticmethod
    def _lock_reason(strategy: AuthenticationStrategy, credentials_provided: bool, route: AuthRouteClassification) -> str:
        if strategy == AuthenticationStrategy.LOGIN_EXISTING_USER and credentials_provided:
            return "Credentials provided; login strategy locked in"
        if strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
            return "No credentials provided; account-creation strategy selected"
        if strategy == AuthenticationStrategy.OAUTH_LOGIN:
            return f"OAuth route detected: {route.route_type.value if hasattr(route.route_type, 'value') else route.route_type}"
        if strategy == AuthenticationStrategy.GUEST_ACCESS:
            return "Guest flow selected or auth not required"
        return "Strategy selected by semantic ranking"

    @staticmethod
    def _reasoning(strategy: AuthenticationStrategy, credentials_provided: bool, requires_auth: bool, route: AuthRouteClassification) -> List[str]:
        reasoning = [f"Route classified as {route.route_type.value if hasattr(route.route_type, 'value') else route.route_type}"]
        if credentials_provided:
            reasoning.append("Credentials detected; login heavily preferred")
        if not credentials_provided and requires_auth:
            reasoning.append("No credentials supplied; account creation is allowed for authenticated exploration")
        if strategy == AuthenticationStrategy.LOGIN_EXISTING_USER:
            reasoning.append("Login candidate scored highest")
        elif strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
            reasoning.append("Signup candidate scored highest")
        elif strategy == AuthenticationStrategy.OAUTH_LOGIN:
            reasoning.append("OAuth candidate scored highest")
        else:
            reasoning.append("Guest flow or auth bypass selected")
        return reasoning

    @staticmethod
    def _route_signals(route_type: str, route_scores: dict[str, float]) -> List[str]:
        signals = [f"{route_type} selected with score {route_scores.get(route_type, 0.0):.2f}"]
        if route_scores.get(AuthRouteType.LOGIN_PAGE.value, 0.0) >= 0.7:
            signals.append("login semantics strong")
        if route_scores.get(AuthRouteType.SIGNUP_PAGE.value, 0.0) >= 0.7:
            signals.append("signup semantics strong")
        if route_scores.get(AuthRouteType.OAUTH_PAGE.value, 0.0) >= 0.7:
            signals.append("oauth semantics strong")
        return signals

    @staticmethod
    def _login_score(combined: str, observation: Observation) -> float:
        score = 0.0
        if any(term in combined for term in ["login", "sign in", "log in", "continue"]):
            score += 0.6
        if any(element.element_type == "password" for element in observation.inputs):
            score += 0.25
        if any(term in combined for term in ["enter your credentials", "access your account", "welcome back"]):
            score += 0.15
        return min(score, 0.99)

    @staticmethod
    def _signup_score(combined: str, observation: Observation) -> float:
        score = 0.0
        if any(term in combined for term in ["sign up", "signup", "register", "create account", "join now", "get started"]):
            score += 0.65
        if len(observation.inputs) >= 3:
            score += 0.15
        if any(term in combined for term in ["confirm password", "create your account"]):
            score += 0.15
        return min(score, 0.99)

    @staticmethod
    def _oauth_score(combined: str) -> float:
        score = 0.0
        if any(term in combined for term in ["oauth", "google", "microsoft", "github", "apple", "sso", "continue with"]):
            score += 0.85
        return min(score, 0.99)

    @staticmethod
    def _forgot_password_score(combined: str) -> float:
        score = 0.0
        if any(term in combined for term in ["forgot password", "reset password", "recover password", "trouble signing in"]):
            score += 0.8
        return min(score, 0.99)

    @staticmethod
    def _dashboard_score(combined: str, observation: Observation) -> float:
        score = 0.0
        if any(term in combined for term in ["dashboard", "overview", "home", "welcome back"]):
            score += 0.65
        if any(term in " ".join(element.label.lower() for element in observation.elements) for term in ["logout", "sign out", "profile", "account"]):
            score += 0.2
        return min(score, 0.99)

    @staticmethod
    def _landing_score(combined: str) -> float:
        score = 0.0
        if any(term in combined for term in ["sign in", "login", "get started", "create account", "try free"]):
            score += 0.4
        return min(score, 0.99)