from __future__ import annotations

from backend.agent.planner.base_planner import BasePlanner, PlannerContext
from backend.agent.services.account_generation_service import AccountGenerationService
from backend.agent.services.auth_strategy_service import AuthStrategyService
from backend.core.models.actions import AgentAction
from backend.core.models.auth import AuthenticationStrategy
from backend.core.models.workflow import ActionType, GoalType, WorkflowState


class LoginPlanner(BasePlanner):
    name = "login_planner"

    def __init__(self) -> None:
        self.auth_strategy_service = AuthStrategyService()
        self.account_generation_service = AccountGenerationService()

    def can_handle(self, context: PlannerContext) -> bool:
        return (
            context.goal == GoalType.AUTHENTICATE_USER
            or context.workflow_state in {WorkflowState.LOGIN_PAGE, WorkflowState.CREDENTIALS_FILLED}
            or context.page.page_type in {"login_page", "signup_page", "oauth_page", "forgot_password_page"}
            or context.page.route_type in {"login_page", "signup_page", "oauth_page", "forgot_password_page"}
        )

    def plan(self, context: PlannerContext):
        strategy = context.auth_strategy or self.auth_strategy_service.select_strategy(
            goal=context.goal,
            workflow_state=context.workflow_state,
            observation=context.observation,
            page_classification=context.page,
            auth_authenticated=context.auth.authenticated,
            credentials=context.credentials,
        )
        reasoning: list[str] = [
            f"Workflow state is {context.workflow_state.value}",
            f"Page classified as {context.page.page_type} ({context.page.confidence:.2f})",
            f"Auth route classified as {context.page.route_type}",
            f"Auth strategy selected: {strategy.strategy.value} ({strategy.mode.value})",
        ]

        if context.auth.authenticated:
            action = AgentAction(
                goal=context.goal,
                workflow_state=WorkflowState.AUTHENTICATED,
                action=ActionType.WAIT,
                confidence=context.auth.confidence,
                reason="Authentication already detected",
                expected_outcome="authenticated session remains available",
            )
            reasoning.extend(context.auth.signals)
            reasoning.extend(strategy.reasoning)
            return self.decision(context, action, reasoning, completed=True)

        credentials = self._resolve_credentials(context, strategy.strategy)
        email_value = credentials.get("email") or credentials.get("username") or credentials.get("user")
        password_value = credentials.get("password")
        email_field = context.form.field("email") or context.form.field("username")
        password_field = context.form.field("password")
        confirm_password_field = context.form.field("confirm_password")
        first_name_field = context.form.field("first_name") or context.form.field("name")
        last_name_field = context.form.field("last_name")
        oauth_button = self._oauth_button(context)

        reasoning.extend(strategy.reasoning)

        if strategy.strategy == AuthenticationStrategy.GUEST_ACCESS:
            action = AgentAction(
                goal=context.goal,
                workflow_state=context.workflow_state,
                action=ActionType.WAIT,
                confidence=strategy.confidence,
                reason="Authentication not required; continue guest flow",
                expected_outcome="guest workflow continues",
            )
            return self.decision(context, action, reasoning, completed=True)

        if strategy.strategy == AuthenticationStrategy.OAUTH_LOGIN and oauth_button:
            reasoning.append("OAuth provider button identified")
            action = AgentAction(
                goal=context.goal,
                workflow_state=WorkflowState.OAUTH_PAGE,
                action=ActionType.CLICK,
                selector=self.selector_for(oauth_button),
                element_index=oauth_button.index,
                target=oauth_button.label,
                confidence=min(oauth_button.selector_candidates[0].score if oauth_button.selector_candidates else 0.8, 0.95),
                reason="Initiate OAuth login",
                expected_outcome="provider authentication flow opens",
                skill_name=self.name,
            )
            return self.decision(context, action, reasoning)

        if strategy.strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT:
            if first_name_field and credentials.get("display_name") and not first_name_field.element.value:
                return self._fill_field(context, first_name_field, credentials.get("display_name"), "Fill signup name", reasoning)
            if email_field and email_value and not email_field.element.value:
                return self._fill_field(context, email_field, email_value, "Fill signup email", reasoning)
            if first_name_field and not first_name_field.element.value and credentials.get("username"):
                return self._fill_field(context, first_name_field, credentials.get("username"), "Fill signup username", reasoning)
            if last_name_field and credentials.get("display_name") and not last_name_field.element.value:
                return self._fill_field(context, last_name_field, credentials.get("display_name"), "Fill signup surname", reasoning)
            if password_field and password_value and not password_field.element.value:
                return self._fill_field(context, password_field, password_value, "Fill signup password", reasoning)
            if confirm_password_field and password_value and not confirm_password_field.element.value:
                return self._fill_field(context, confirm_password_field, password_value, "Fill password confirmation", reasoning)
            if context.form.submit_button:
                btn = context.form.submit_button
                reasoning.append("Signup form ready to submit")
                selector = self.selector_for(btn)
                action = AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.SIGNUP_PAGE,
                    action=ActionType.SUBMIT,
                    selector=selector,
                    element_index=btn.index,
                    target=btn.label,
                    confidence=0.92,
                    reason="Submit signup form",
                    expected_outcome="new account is created and authentication is established",
                    skill_name=self.name,
                )
                return self.decision(context, action, reasoning)

        if strategy.strategy == AuthenticationStrategy.LOGIN_EXISTING_USER:
            if email_field and email_value and not email_field.element.value:
                reasoning.extend(["Email/username field identified", "Credentials are available"])
                action = AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.LOGIN_PAGE,
                    action=ActionType.FILL,
                    selector=self.selector_for(email_field.element),
                    element_index=email_field.element.index,
                    target=email_field.element.label,
                    value=email_value,
                    confidence=min(email_field.confidence, 0.97),
                    reason="Fill login identifier field",
                    expected_outcome="login identifier is entered",
                )
                return self.decision(context, action, reasoning)

            if password_field and password_value and not password_field.element.value:
                reasoning.extend(["Password field identified", "Password credential is available"])
                action = AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.LOGIN_PAGE,
                    action=ActionType.FILL,
                    selector=self.selector_for(password_field.element),
                    element_index=password_field.element.index,
                    target=password_field.element.label,
                    value=password_value,
                    confidence=min(password_field.confidence, 0.98),
                    reason="Fill password field",
                    expected_outcome="password is entered",
                )
                return self.decision(context, action, reasoning)

            if context.form.submit_button:
                reasoning.extend(["Login form fields appear filled or unavailable", "Submit button detected"])
                action = AgentAction(
                    goal=context.goal,
                    workflow_state=WorkflowState.CREDENTIALS_FILLED,
                    action=ActionType.SUBMIT,
                    selector=self.selector_for(context.form.submit_button),
                    element_index=context.form.submit_button.index,
                    target=context.form.submit_button.label,
                    confidence=0.9,
                    reason="Submit login form",
                    expected_outcome="authenticated dashboard or account area appears",
                    skill_name=self.name,
                )
                return self.decision(context, action, reasoning)

        reasoning.append("Authentication flow requires additional recovery or route discovery")
        action = AgentAction(
            goal=context.goal,
            workflow_state=context.workflow_state,
            action=ActionType.WAIT,
            confidence=0.58,
            reason="Await auth page stabilization or route recovery",
            expected_outcome="auth route becomes stable enough to continue",
            skill_name=self.name,
        )
        return self.decision(context, action, reasoning, replan=True)

    def _resolve_credentials(self, context: PlannerContext, strategy: AuthenticationStrategy) -> dict[str, str]:
        credentials = dict(context.credentials or {})
        if strategy == AuthenticationStrategy.CREATE_NEW_ACCOUNT and not credentials:
            generated = self.account_generation_service.generate(base_domain=context.observation.url)
            credentials.update(generated.model_dump(mode="json"))
        return credentials

    def _fill_field(self, context: PlannerContext, field, value: str, reason: str, reasoning: list[str]):
        selector = self.selector_for(field.element)
        reasoning.append(reason)
        return self.decision(
            context,
            AgentAction(
                goal=context.goal,
                workflow_state=WorkflowState.SIGNUP_PAGE if "signup" in reason.lower() else WorkflowState.LOGIN_PAGE,
                action=ActionType.FILL,
                selector=selector,
                element_index=field.element.index,
                target=field.element.label,
                value=value,
                confidence=min(field.confidence, 0.98),
                reason=reason,
                expected_outcome=f"{field.semantic_type} field is entered",
                skill_name=self.name,
            ),
            reasoning,
        )

    def _oauth_button(self, context: PlannerContext):
        candidates = [
            element
            for element in context.observation.elements
            if element.visible and element.enabled and element.label.lower()
        ]
        preferred = [
            element
            for element in candidates
            if any(term in element.label.lower() for term in ["google", "microsoft", "github", "apple", "oauth", "single sign on", "continue with"])
        ]
        return preferred[0] if preferred else None