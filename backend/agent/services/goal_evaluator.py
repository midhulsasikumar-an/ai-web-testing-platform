from __future__ import annotations

from backend.core.models.observations import Observation
from backend.core.models.semantic_state import GoalEvaluation, NavigationTransition, PageClassification
from backend.core.models.workflow import WorkflowState


class GoalEvaluator:
    def evaluate(
        self,
        goal: str,
        observation: Observation,
        page_classification: PageClassification,
        transition: NavigationTransition | None = None,
        workflow_state: WorkflowState | None = None,
        authenticated: bool = False,
    ) -> GoalEvaluation:
        normalized_goal = goal.lower().replace("-", "_").replace(" ", "_")
        goal_kinds = self._goal_kinds(normalized_goal)
        if len(goal_kinds) > 1:
            return self._evaluate_compound(goal, goal_kinds, observation, page_classification, transition, workflow_state, authenticated)
        if any(term in normalized_goal for term in ["login", "auth", "authenticate", "sign_in"]):
            return self._evaluate_auth(goal, observation, page_classification, workflow_state, authenticated)
        if any(term in normalized_goal for term in ["admin", "user_management", "users", "navigate_admin"]):
            return self._evaluate_admin(goal, observation, page_classification, transition)
        if any(term in normalized_goal for term in ["settings", "preferences", "open_settings"]):
            return self._evaluate_settings(goal, observation, page_classification, transition)
        return self._evaluate_generic(goal, observation, page_classification, transition)

    @staticmethod
    def _goal_kinds(normalized_goal: str) -> list[str]:
        kinds: list[str] = []
        if any(term in normalized_goal for term in ["login", "auth", "authenticate", "sign_in"]):
            kinds.append("auth")
        if any(term in normalized_goal for term in ["admin", "user_management", "users", "navigate_admin"]):
            kinds.append("admin")
        if any(term in normalized_goal for term in ["settings", "preferences", "open_settings"]):
            kinds.append("settings")
        return kinds

    def _evaluate_compound(
        self,
        goal: str,
        goal_kinds: list[str],
        observation: Observation,
        page_classification: PageClassification,
        transition: NavigationTransition | None,
        workflow_state: WorkflowState | None,
        authenticated: bool,
    ) -> GoalEvaluation:
        evaluations: list[GoalEvaluation] = []
        if "auth" in goal_kinds:
            evaluations.append(self._evaluate_auth(goal, observation, page_classification, workflow_state, authenticated))
        if "admin" in goal_kinds:
            evaluations.append(self._evaluate_admin(goal, observation, page_classification, transition))
        if "settings" in goal_kinds:
            evaluations.append(self._evaluate_settings(goal, observation, page_classification, transition))

        matched: list[str] = []
        missing: list[str] = []
        reasoning: list[str] = ["Evaluated compound goal sequence across multiple semantic objectives."]
        for evaluation in evaluations:
            matched.extend(evaluation.matched_conditions)
            missing.extend(evaluation.missing_conditions)
            reasoning.extend(evaluation.reasoning)
        confidence = sum(evaluation.confidence for evaluation in evaluations) / max(len(evaluations), 1)
        goal_completed = all(evaluation.goal_completed for evaluation in evaluations)
        return GoalEvaluation(
            goal_completed=goal_completed,
            confidence=min(confidence, 0.99),
            matched_conditions=matched,
            missing_conditions=missing,
            reasoning=reasoning,
            goal_name=goal,
            semantic_state=page_classification.semantic_state or page_classification.page_type,
        )

    def _evaluate_auth(
        self,
        goal: str,
        observation: Observation,
        page_classification: PageClassification,
        workflow_state: WorkflowState | None,
        authenticated: bool,
    ) -> GoalEvaluation:
        matched: list[str] = []
        missing: list[str] = []
        reasoning: list[str] = []
        confidence = 0.0

        if workflow_state in {WorkflowState.AUTHENTICATED, WorkflowState.DASHBOARD, WorkflowState.DASHBOARD_HOME}:
            matched.append("workflow state indicates authenticated session")
            confidence += 0.28
        else:
            missing.append("workflow state indicates authenticated session")

        if authenticated or page_classification.page_type in {"dashboard_home", "dashboard", "admin_module", "user_management"} or any(term in observation.page_text.lower() for term in ["logout", "profile", "account", "sign out"]):
            matched.append("authentication indicators visible")
            confidence += 0.36
        else:
            missing.append("authentication indicators visible")

        if page_classification.page_type in {"dashboard_home", "dashboard", "admin_module", "user_management"}:
            matched.append("redirected away from login page")
            confidence += 0.24
        else:
            missing.append("redirected away from login page")

        if page_classification.page_type in {"dashboard_home", "dashboard", "admin_module", "user_management"} or any(term in (observation.title + " " + observation.page_text).lower() for term in ["dashboard", "home", "welcome", "admin", "users"]):
            matched.append("dashboard visible")
            confidence += 0.14
        else:
            missing.append("dashboard visible")

        reasoning.append(f"Evaluated authentication goal '{goal}' against the current semantic state.")
        return GoalEvaluation(
            goal_completed=len(missing) == 0 or confidence >= 0.72,
            confidence=min(confidence, 0.99),
            matched_conditions=matched,
            missing_conditions=[] if len(missing) == 0 or confidence >= 0.72 else missing,
            reasoning=reasoning,
            goal_name=goal,
            semantic_state=page_classification.semantic_state or page_classification.page_type,
        )

    def _evaluate_admin(
        self,
        goal: str,
        observation: Observation,
        page_classification: PageClassification,
        transition: NavigationTransition | None,
    ) -> GoalEvaluation:
        matched: list[str] = []
        missing: list[str] = []
        reasoning: list[str] = []
        confidence = 0.0
        text = f"{observation.title} {' '.join(observation.headings)} {observation.page_text}".lower()

        if page_classification.page_type in {"admin_module", "user_management", "table_page", "listing_page"}:
            matched.append("admin or user-management page detected")
            confidence += 0.4
        else:
            missing.append("admin or user-management page detected")

        if any(term in text for term in ["system users", "user management", "admin", "users", "roles", "permissions"]):
            matched.append("admin module content visible")
            confidence += 0.26
        else:
            missing.append("admin module content visible")

        if any(term in text for term in ["table", "search", "filter", "pagination", "rows"]):
            matched.append("table visible")
            confidence += 0.2
        else:
            missing.append("table visible")

        if transition and transition.navigation_type in {"sidebar_transition", "module_transition"}:
            matched.append(f"{transition.navigation_type} detected")
            confidence += 0.12
            reasoning.append(transition.summary)
        elif transition:
            reasoning.append(f"Observed transition type: {transition.navigation_type}")

        if transition and transition.to_state in {"admin_module", "user_management"}:
            matched.append(f"transitioned to {transition.to_state}")
            confidence += 0.12

        reasoning.append(f"Evaluated admin-navigation goal '{goal}'.")
        return GoalEvaluation(
            goal_completed=len(missing) <= 1 or confidence >= 0.72,
            confidence=min(confidence, 0.99),
            matched_conditions=matched,
            missing_conditions=[] if len(missing) <= 1 or confidence >= 0.72 else missing,
            reasoning=reasoning,
            goal_name=goal,
            semantic_state=page_classification.semantic_state or page_classification.page_type,
        )

    def _evaluate_settings(
        self,
        goal: str,
        observation: Observation,
        page_classification: PageClassification,
        transition: NavigationTransition | None,
    ) -> GoalEvaluation:
        matched: list[str] = []
        missing: list[str] = []
        reasoning: list[str] = []
        confidence = 0.0
        text = f"{observation.title} {' '.join(observation.headings)} {observation.page_text}".lower()

        if page_classification.page_type == "settings_page":
            matched.append("settings page classified")
            confidence += 0.35
        else:
            missing.append("settings page classified")

        if any(term in text for term in ["settings", "preferences", "configuration", "profile settings"]):
            matched.append("settings text visible")
            confidence += 0.25
        else:
            missing.append("settings text visible")

        if observation.forms:
            matched.append("settings form visible")
            confidence += 0.2
        else:
            missing.append("settings form visible")

        if any(term in text for term in ["breadcrumb", "settings"]):
            matched.append("settings breadcrumb visible")
            confidence += 0.1

        if transition and transition.to_state == "settings_page":
            matched.append("transitioned to settings page")
            confidence += 0.1
            reasoning.append(transition.summary)

        reasoning.append(f"Evaluated settings goal '{goal}'.")
        return GoalEvaluation(
            goal_completed=len(missing) <= 1 or confidence >= 0.7,
            confidence=min(confidence, 0.99),
            matched_conditions=matched,
            missing_conditions=[] if len(missing) <= 1 or confidence >= 0.7 else missing,
            reasoning=reasoning,
            goal_name=goal,
            semantic_state=page_classification.semantic_state or page_classification.page_type,
        )

    def _evaluate_generic(
        self,
        goal: str,
        observation: Observation,
        page_classification: PageClassification,
        transition: NavigationTransition | None,
    ) -> GoalEvaluation:
        goal_terms = [term for term in goal.lower().replace("-", " ").replace("_", " ").split() if len(term) > 3]
        haystack = f"{observation.title} {' '.join(observation.headings)} {observation.page_text} {page_classification.page_type}".lower()
        matched = [term for term in goal_terms if term in haystack]
        missing = [term for term in goal_terms if term not in haystack]
        reasoning = [f"Matched {len(matched)} of {len(goal_terms)} goal terms against visible semantic content."]
        if transition and transition.semantic_change:
            reasoning.append(transition.summary)
        confidence = 0.2 + (0.18 * len(matched))
        return GoalEvaluation(
            goal_completed=bool(goal_terms) and len(missing) <= max(1, len(goal_terms) // 2),
            confidence=min(confidence, 0.99),
            matched_conditions=matched,
            missing_conditions=missing,
            reasoning=reasoning,
            goal_name=goal,
            semantic_state=page_classification.semantic_state or page_classification.page_type,
        )
