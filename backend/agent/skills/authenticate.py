"""
Authenticate skill — handles login flows including credential filling,
form submission, MFA detection, and post-login validation.
"""

from __future__ import annotations

from typing import List, Optional

from backend.agent.services.account_generation_service import AccountGenerationService
from backend.agent.services.auth_strategy_service import AuthStrategyService
from backend.config.agent_config import get_config
from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillResult
from backend.core.models.actions import AgentAction
from backend.core.models.auth import AuthenticationStrategy
from backend.core.models.planner import RiskAssessment
from backend.core.models.workflow import ActionType, GoalType, WorkflowState


class AuthenticateSkill(BaseSkill):
    name = "authenticate"
    description = "Handle login/authentication flows including credential fill and form submission"
    version = "2.0.0"
    priority = 95
    tags = ["auth", "login", "credentials"]

    def __init__(self) -> None:
        self.auth_strategy_service = AuthStrategyService()
        self.account_generation_service = AccountGenerationService()

    def applicability_score(self, context: SkillContext) -> float:
        score = 0.0
        if context.goal == GoalType.AUTHENTICATE_USER:
            score += 0.4
        if context.workflow_state in {WorkflowState.LOGIN_PAGE, WorkflowState.CREDENTIALS_FILLED, WorkflowState.SIGNUP_PAGE, WorkflowState.OAUTH_PAGE}:
            score += 0.3
        if context.page_classification.page_type in {"login_page", "signup_page", "oauth_page", "forgot_password_page"}:
            score += 0.25
        if context.auth_result.authenticated:
            score += 0.05  # low — mostly done
        if context.form_analysis.field("password"):
            score += 0.15
        if context.auth_strategy:
            if context.auth_strategy.strategy == AuthenticationStrategy.LOGIN_EXISTING_USER:
                score += 0.15
            elif context.auth_strategy.strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
                score += 0.18
            elif context.auth_strategy.strategy == AuthenticationStrategy.OAUTH_LOGIN:
                score += 0.1
        return min(score, 1.0)

    def check_preconditions(self, context: SkillContext) -> tuple[bool, str]:
        if context.auth_result.authenticated:
            return True, "Already authenticated"
        route_type = context.page_classification.route_type
        if route_type in {"login_page", "signup_page", "oauth_page", "forgot_password_page"}:
            return True, f"Auth route detected: {route_type}"
        if context.page_classification.page_type != "login_page" and not context.form_analysis.field("password"):
            return False, "Not on an auth page and no password field detected"
        return True, "Authentication flow detected"

    def plan(self, context: SkillContext) -> SkillResult:
        strategy = context.auth_strategy or self.auth_strategy_service.select_strategy(
            goal=context.goal,
            workflow_state=context.workflow_state,
            observation=context.observation,
            page_classification=context.page_classification,
            auth_authenticated=context.auth_result.authenticated,
            credentials=context.credentials,
        )
        reasoning: List[str] = [
            f"Workflow state: {context.workflow_state.value}",
            f"Page type: {context.page_classification.page_type} ({context.page_classification.confidence:.2f})",
            f"Auth route: {context.page_classification.route_type}",
            f"Auth strategy: {strategy.strategy.value} ({strategy.mode.value})",
        ]

        if context.auth_result.authenticated:
            reasoning.extend(context.auth_result.signals)
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.AUTHENTICATED,
                    action=ActionType.WAIT,
                    confidence=context.auth_result.confidence,
                    reason="Authentication already detected",
                    expected_outcome="authenticated session remains available",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=context.auth_result.confidence,
                completed=True,
                expected_outcome="authenticated session active",
            )

        credentials = self._resolve_credentials(context, strategy.strategy)
        email_value = credentials.get("email") or credentials.get("username") or credentials.get("user")
        password_value = credentials.get("password")
        email_field = context.form_analysis.field("email") or context.form_analysis.field("username")
        password_field = context.form_analysis.field("password")
        confirm_password_field = context.form_analysis.field("confirm_password")
        first_name_field = context.form_analysis.field("first_name") or context.form_analysis.field("name")
        last_name_field = context.form_analysis.field("last_name")
        oauth_button = self._oauth_button(context)

        reasoning.extend(strategy.reasoning)

        if strategy.strategy == AuthenticationStrategy.GUEST_ACCESS:
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=context.workflow_state,
                    action=ActionType.WAIT,
                    confidence=strategy.confidence,
                    reason="Guest flow selected; authentication not required",
                    expected_outcome="guest workflow continues",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=strategy.confidence,
                completed=True,
                expected_outcome="guest access active",
            )

        if strategy.strategy == AuthenticationStrategy.OAUTH_LOGIN and oauth_button:
            reasoning.append("OAuth provider control detected")
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.OAUTH_PAGE,
                    action=ActionType.CLICK,
                    selector=self.selector_for(oauth_button),
                    element_index=oauth_button.index,
                    target=oauth_button.label,
                    confidence=min(oauth_button.selector_candidates[0].score if oauth_button.selector_candidates else 0.85, 0.95),
                    reason="Begin OAuth login",
                    expected_outcome="identity provider flow opens",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=0.9,
                expected_outcome="oauth flow opened",
            )

        if strategy.strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
            generated = context.credentials or self.account_generation_service.generate(base_domain=context.observation.url).model_dump(mode="json")
            if first_name_field and generated.get("display_name") and not first_name_field.element.value:
                return self._fill_field(context, first_name_field, generated.get("display_name"), reasoning, WorkflowState.SIGNUP_PAGE)
            if email_field and email_value and not email_field.element.value:
                return self._fill_field(context, email_field, email_value, reasoning, WorkflowState.SIGNUP_PAGE)
            if last_name_field and generated.get("display_name") and not last_name_field.element.value:
                return self._fill_field(context, last_name_field, generated.get("display_name"), reasoning, WorkflowState.SIGNUP_PAGE)
            if password_field and password_value and not password_field.element.value:
                return self._fill_field(context, password_field, password_value, reasoning, WorkflowState.SIGNUP_PAGE)
            if confirm_password_field and password_value and not confirm_password_field.element.value:
                return self._fill_field(context, confirm_password_field, password_value, reasoning, WorkflowState.SIGNUP_PAGE)
            if context.form_analysis.submit_button:
                btn = context.form_analysis.submit_button
                reasoning.append("Signup form ready to submit")
                # Respect allow_account_creation safety toggle
                if not get_config().allow_account_creation:
                    reasoning.append("Account creation disabled by configuration: running validation-only checks")
                    return SkillResult(
                        action=AgentAction(
                            goal=context.goal,
                            workflow_state=WorkflowState.SIGNUP_PAGE,
                            action=ActionType.WAIT,
                            confidence=0.6,
                            reason="Validation-only signup (no submit)",
                            expected_outcome="signup form validated without creating real account",
                            skill_name=self.name,
                        ),
                        reasoning=reasoning,
                        confidence=0.6,
                        expected_outcome="signup validation performed",
                    )
                return SkillResult(
                    action=AgentAction(
                        goal=context.goal,
                        workflow_state=WorkflowState.SIGNUP_PAGE,
                        action=ActionType.SUBMIT,
                        selector=self.selector_for(btn),
                        element_index=btn.index,
                        target=btn.label,
                        confidence=0.92,
                        reason="Submit signup form",
                        expected_outcome="account is created and session is established",
                        skill_name=self.name,
                    ),
                    reasoning=reasoning,
                    confidence=0.92,
                    expected_outcome="new account created",
                )

        if email_field and email_value and not email_field.element.value:
            reasoning.extend(["Email/username field identified", "Credentials available"])
            selector = email_field.element.selector_candidates[0].selector if email_field.element.selector_candidates else None
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.LOGIN_PAGE,
                    action=ActionType.FILL,
                    selector=selector,
                    element_index=email_field.element.index,
                    target=email_field.element.label,
                    value=email_value,
                    confidence=min(email_field.confidence, 0.97),
                    reason="Fill login identifier field",
                    expected_outcome="login identifier is entered",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=min(email_field.confidence, 0.97),
                expected_outcome="login identifier entered in field",
            )

        if password_field and password_value and not password_field.element.value:
            reasoning.extend(["Password field identified", "Password credential available"])
            selector = password_field.element.selector_candidates[0].selector if password_field.element.selector_candidates else None
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.LOGIN_PAGE,
                    action=ActionType.FILL,
                    selector=selector,
                    element_index=password_field.element.index,
                    target=password_field.element.label,
                    value=password_value,
                    confidence=min(password_field.confidence, 0.98),
                    reason="Fill password field",
                    expected_outcome="password is entered",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=min(password_field.confidence, 0.98),
                expected_outcome="password entered in field",
            )

        if context.form_analysis.submit_button:
            btn = context.form_analysis.submit_button
            reasoning.extend(["Form fields filled or unavailable", "Submit button detected"])
            selector = btn.selector_candidates[0].selector if btn.selector_candidates else None
            return SkillResult(
                action=AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.CREDENTIALS_FILLED,
                    action=ActionType.SUBMIT,
                    selector=selector,
                    element_index=btn.index,
                    target=btn.label,
                    confidence=0.9,
                    reason="Submit login form",
                    expected_outcome="authenticated dashboard or account area appears",
                    skill_name=self.name,
                ),
                reasoning=reasoning,
                confidence=0.9,
                expected_outcome="user is authenticated and redirected",
                risk=RiskAssessment(risk_score=0.1, safety_level="safe"),
            )

        reasoning.append("Login page detected but required fields or credentials missing")
        return SkillResult(
            action=AgentAction(
                goal=context.goal,
                workflow_state=WorkflowState.LOGIN_PAGE,
                action=ActionType.SCROLL,
                value="700",
                confidence=0.62,
                reason="Search for missing login controls",
                expected_outcome="more login form controls become visible",
                skill_name=self.name,
            ),
            reasoning=reasoning,
            confidence=0.62,
            replan=True,
            expected_outcome="login form controls revealed",
        )

    def _resolve_credentials(self, context: SkillContext, strategy: AuthenticationStrategy) -> dict[str, str]:
        credentials = dict(context.credentials or {})
        if strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT and not credentials:
            generated = self.account_generation_service.generate(base_domain=context.observation.url)
            credentials.update(generated.model_dump(mode="json"))
        return credentials

    def _fill_field(self, context: SkillContext, field, value: str, reasoning: List[str], workflow_state: WorkflowState) -> SkillResult:
        selector = field.element.selector_candidates[0].selector if field.element.selector_candidates else None
        reasoning.append(f"Filling {field.semantic_type} field for {workflow_state.value.lower()}")
        return SkillResult(
            action=AgentAction(
                goal=context.goal,
                workflow_state=workflow_state,
                action=ActionType.FILL,
                selector=selector,
                element_index=field.element.index,
                target=field.element.label,
                value=value,
                confidence=min(field.confidence, 0.98),
                reason=f"Fill {field.semantic_type} field",
                expected_outcome=f"{field.semantic_type} field is entered",
                skill_name=self.name,
            ),
            reasoning=reasoning,
            confidence=min(field.confidence, 0.98),
            expected_outcome=f"{field.semantic_type} field entered",
        )

    def _oauth_button(self, context: SkillContext):
        candidates = [element for element in context.observation.elements if element.visible and element.enabled]
        preferred = [
            element
            for element in candidates
            if any(term in element.label.lower() for term in ["google", "microsoft", "github", "apple", "oauth", "single sign on", "continue with"])
        ]
        return preferred[0] if preferred else None

    def recovery_fallback(self, context: SkillContext, failure_reason: str) -> Optional[SkillResult]:
        return SkillResult(
            action=AgentAction(
                goal=context.goal,
                workflow_state=context.workflow_state,
                action=ActionType.WAIT,
                confidence=0.5,
                reason=f"Auth recovery: {failure_reason}",
                skill_name=self.name,
            ),
            reasoning=["Authentication skill failed", f"Failure: {failure_reason}", "Waiting for page stability"],
            confidence=0.5,
            replan=True,
            expected_outcome="page stabilizes for retry",
        )

    def expected_outcomes(self) -> List[str]:
        return ["user authenticated", "dashboard visible", "session cookie set"]
