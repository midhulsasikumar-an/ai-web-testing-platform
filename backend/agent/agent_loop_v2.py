"""
Upgraded Autonomous Agent Loop — Production-grade, goal-driven,
skill-based, multimodal intelligent agent execution engine.

This is the core orchestration loop that integrates:
- World model / navigation graph
- Skill-based dynamic planning
- Objective-driven execution
- Advanced memory (episodic, semantic, procedural)
- Visual reasoning
- Risk assessment
- Reasoning trace engine
- Advanced loop prevention
- Context window management
- Observability / telemetry
- Trajectory scoring for RL

It preserves full backward compatibility with the existing agent loop
while adding all enterprise-grade capabilities.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from playwright.async_api import Page

from backend.agent.browser_session import BrowserSignals
from backend.agent.executor import ActionExecutor
from backend.agent.memory_service import AgentMemory
from backend.agent.observer import BrowserObserver
from backend.agent.outcome import OutcomeValidator
from backend.agent.planner import PlannerContext, PlannerOrchestrator
from backend.agent.recovery import RecoveryEngine
from backend.agent.safety import SafetyPolicy
from backend.core.models.actions import ActionResult
from backend.core.models.agent_state import AgentRunState, AgentStep
from backend.core.models.workflow import FailureType, GoalType, WorkflowState
from backend.core.models.planner import PlannerDecision
from backend.agent.services.auth_detector import AuthDetector
from backend.agent.services.auth_strategy_service import AuthStrategyService
from backend.agent.services.form_service import FormIntelligenceService
from backend.agent.services.frontier_service import FrontierService
from backend.agent.services.observation_diff import ObservationDiffService
from backend.agent.services.goal_evaluator import GoalEvaluator
from backend.agent.services.navigation_state_service import NavigationStateService
from backend.agent.services.page_classifier import PageClassifier
from backend.agent.services.stability_service import StabilityService
from backend.agent.validator import ActionValidationEngine
from backend.accessibility.service import AccessibilityAuditService
from backend.events.bus import ExecutionEventBus
from backend.events.schemas import ExecutionEvent, ExecutionEventType
from backend.agent.live_reasoning.engine import LiveReasoningEngine
from backend.services.performance_analysis_service import analyze_performance
from backend.services.bug_clustering_service import cluster_bugs

# New subsystems
from backend.agent.world_model.world_graph import WorldGraph
from backend.agent.world_model.trajectory_engine import TrajectoryEngine
from backend.agent.skill_engine.skill_registry import BaseSkill, SkillRegistry
from backend.agent.skill_engine.skill_context import SkillContext
from backend.agent.skill_engine.skill_selector import SkillSelector
from backend.agent.skill_engine.skill_router import SkillRouter
from backend.agent.skills.authenticate import AuthenticateSkill
from backend.agent.skills.dismiss_modal import DismissModalSkill
from backend.agent.skills.complete_form import CompleteFormSkill
from backend.agent.skills.navigate_sidebar import NavigateSidebarSkill
from backend.agent.skills.search_site import SearchSiteSkill
from backend.agent.skills.resolve_overlay import ResolveOverlaySkill
from backend.agent.skills.recover_navigation import RecoverNavigationSkill
from backend.agent.skills.detect_dashboard import (
    DetectDashboardSkill, ValidatePageSkill, PaginationSkill,
)
from backend.agent.objectives.objective import ExecutionPlan
from backend.agent.memory.episodic_memory import EpisodicMemory
from backend.agent.memory.semantic_memory import SemanticMemory
from backend.agent.memory.procedural_memory import ProceduralMemory
from backend.agent.memory.memory_retriever import MemoryRetriever
from backend.agent.safety.action_risk_engine import ActionRiskEngine
from backend.agent.reasoning.reasoning_trace import ReasoningTraceEngine
from backend.agent.loop_prevention.trajectory_analyzer import TrajectoryAnalyzer
from backend.agent.context.context_window_manager import ReasoningContextBuilder
from backend.agent.vision.visual_diff import VisualDiff
from backend.observability.observability import (
    StructuredLogger, MetricsCollector, ExecutionTelemetry,
)
from backend.config.agent_config import get_config

logger = logging.getLogger("agent.autonomous.v2")
logger.addHandler(logging.NullHandler())


class AutonomousAgentLoopV2:
    """
    Production-grade autonomous agent loop with full enterprise capabilities.

    Integrates world model, skill engine, objective decomposition,
    advanced memory, risk assessment, reasoning traces, loop prevention,
    and observability into a unified execution engine.
    """

    def __init__(
        self,
        safety_policy: SafetyPolicy,
        observer: Optional[BrowserObserver] = None,
        planner: Optional[PlannerOrchestrator] = None,
    ):
        config = get_config()

        # Core subsystems (backward compatible)
        self.safety_policy = safety_policy
        self.observer = observer or BrowserObserver()
        self.legacy_planner = planner or PlannerOrchestrator()
        self.validator = ActionValidationEngine(safety_policy)
        self.executor = ActionExecutor(
            selector_engine=self.observer.selector_engine,
            safety_policy=safety_policy,
        )
        self.recovery = RecoveryEngine(self.observer, self.executor)
        self.outcome_validator = OutcomeValidator()
        self.page_classifier = PageClassifier()
        self.form_service = FormIntelligenceService()
        self.auth_detector = AuthDetector()
        self.auth_strategy_service = AuthStrategyService()
        self.diff_service = ObservationDiffService()
        self.navigation_state = NavigationStateService()
        self.goal_evaluator = GoalEvaluator()
        self.stability_service = StabilityService()
        self.accessibility_audit = AccessibilityAuditService()
        self.live_reasoning = LiveReasoningEngine()
        self.frontier = FrontierService(safety_policy)

        # World model
        self.world_graph = WorldGraph()
        self.trajectory_engine = TrajectoryEngine()

        # Skill engine
        self.skill_registry = SkillRegistry()
        self._register_default_skills()
        self.skill_router = SkillRouter(self.skill_registry)

        # Advanced memory
        self.episodic_memory = EpisodicMemory()
        self.semantic_memory = SemanticMemory()
        self.procedural_memory = ProceduralMemory()
        self.memory_retriever = MemoryRetriever(
            self.episodic_memory, self.semantic_memory, self.procedural_memory,
        )

        # Risk engine
        self.risk_engine = ActionRiskEngine()

        # Reasoning traces
        self.reasoning_trace = ReasoningTraceEngine()

        # Loop prevention
        self.loop_analyzer = TrajectoryAnalyzer()

        # Context management
        self.context_builder = ReasoningContextBuilder()

        # Visual diff
        self.visual_diff = VisualDiff()

        # Observability
        self.slogger = StructuredLogger("agent.v2")
        self.metrics = MetricsCollector()
        self.telemetry = ExecutionTelemetry(self.metrics)

        # Feature flags
        self._features = config.features

    def _register_default_skills(self) -> None:
        """Register all built-in skills."""
        for skill_class in [
            AuthenticateSkill, DismissModalSkill, CompleteFormSkill,
            NavigateSidebarSkill, SearchSiteSkill, ResolveOverlaySkill,
            RecoverNavigationSkill, DetectDashboardSkill,
            ValidatePageSkill, PaginationSkill,
        ]:
            self.skill_registry.register(skill_class())

    async def run(
        self,
        page: Page,
        start_url: str,
        goal: str,
        credentials: Optional[dict[str, str]] = None,
        max_steps: int = 30,
        max_retries_per_action: int = 2,
        signals: Optional[BrowserSignals] = None,
        run_id: Optional[str] = None,
        event_bus: Optional[ExecutionEventBus] = None,
    ) -> AgentRunState:
        """Execute the full autonomous agent loop."""
        run_id = run_id or str(uuid.uuid4())
        goal_type = self._goal_type(goal)
        workflow_state = WorkflowState.INIT

        run = AgentRunState(
            run_id=run_id, start_url=start_url, goal=goal,
            max_steps=max_steps, max_retries_per_action=max_retries_per_action,
            current_url=page.url, workflow_state=workflow_state,
        )

        # Initialize subsystems for this run
        memory = AgentMemory(goal=goal)
        previous_observation = None
        execution_plan = ExecutionPlan.decompose_goal(goal) if self._features.enable_objective_decomposition else None
        self.trajectory_engine.start_trajectory(run_id, goal)
        self.slogger.set_context(run_id=run_id, goal=goal)

        # Validate start URL
        start_policy = self.safety_policy.validate_start_url()
        if not start_policy.valid:
            run.status = "blocked"
            run.completed_at = datetime.utcnow()
            run.summary = {"reason": start_policy.reason}
            return run

        self.slogger.info("agent_run_started", url=start_url, max_steps=max_steps)
        run_start_time = time.perf_counter()

        semantic_transitions: list[dict] = []
        goal_evaluations: list[dict] = []
        detected_semantic_states: list[str] = []
        accessibility_findings: list[dict] = []
        performance_findings: list[dict] = []
        timeline_events: list[dict] = []
        event_sequence = 0

        async def publish_event(event_type: ExecutionEventType, message: str, **payload: object) -> None:
            nonlocal event_sequence
            if not event_bus:
                return
            event_sequence += 1
            await event_bus.publish(
                ExecutionEvent(
                    run_id=run_id,
                    type=event_type,
                    message=message,
                    sequence=event_sequence,
                    workflow_state=workflow_state.value,
                    url=page.url,
                    payload={k: v for k, v in payload.items() if v is not None},
                )
            )

        await publish_event(ExecutionEventType.RUN_STATUS, "Agent run started", goal=goal, start_url=start_url)

        for step_number in range(max_steps):
            step_start = time.perf_counter()
            run.current_step = step_number

            await self.stability_service.wait_for_stable(page)

            # ─── OBSERVE ───
            signal_snapshot = signals.snapshot() if signals else {}
            observation = await self.observer.observe(
                page=page, run_id=run_id, step=step_number,
                console_errors=signal_snapshot.get("console_errors"),
                network_failures=signal_snapshot.get("network_failures"),
                dialogs=signal_snapshot.get("dialogs"),
                popups=signal_snapshot.get("popups"),
            )

            # Classify page
            page_classification = self.page_classifier.classify(observation)
            form_analysis = self.form_service.analyze(observation)
            auth_result = await self.auth_detector.detect(observation, page.context)
            auth_strategy = self.auth_strategy_service.select_strategy(
                goal=goal_type,
                workflow_state=workflow_state,
                observation=observation,
                page_classification=page_classification,
                auth_authenticated=auth_result.authenticated,
                credentials=credentials,
            )
            semantic_state = self.navigation_state.classify_state(observation, page_classification, auth_result.authenticated)
            detected_semantic_states.append(semantic_state)
            accessibility_snapshot = self.accessibility_audit.audit(observation)
            accessibility_findings.extend(accessibility_snapshot.get("findings", []))
            if event_bus:
                for finding in accessibility_snapshot.get("findings", []):
                    await publish_event(
                        ExecutionEventType.ACCESSIBILITY_FINDING,
                        finding.get("description", "Accessibility finding detected"),
                        severity=finding.get("severity"),
                        finding=finding,
                    )
                await publish_event(
                    ExecutionEventType.AGENT_REASONING,
                    self.live_reasoning.narrate_observation(page_classification.page_type, observation.url, page_classification.confidence, f"Semantic state {semantic_state}"),
                    confidence=page_classification.confidence,
                    workflow_state=semantic_state,
                )

            # Workflow transition
            workflow_before = workflow_state
            workflow_state = self.navigation_state.resolve_workflow_state(
                workflow_state, observation, page_classification, auth_result.authenticated,
            )
            observation.page_type = page_classification.page_type
            run.workflow_state = workflow_state
            run.current_url = observation.url

            if observation.screenshot:
                run.artifacts.append(observation.screenshot)
                timeline_events.append({"type": "screenshot", "path": observation.screenshot.path, "step": step_number})
                await publish_event(ExecutionEventType.SCREENSHOT, "Captured observation screenshot", screenshot=observation.screenshot.path)

            # ─── WORLD MODEL UPDATE ───
            prev_node_id = self.world_graph.current_node.node_id if self.world_graph.current_node else ""
            current_node = self.world_graph.add_or_update_node(
                url=observation.url,
                dom_fingerprint=observation.fingerprint,
                page_type=observation.page_type,
                workflow_state=workflow_state.value,
                headings=observation.headings,
                form_count=len(observation.forms),
                interactive_element_count=len(observation.elements),
                parent_node_id=prev_node_id or None,
            )
            is_new_state = current_node.visit_count == 1

            # ─── MEMORY UPDATE ───
            memory.remember_observation(observation, step_number)
            diff = self.diff_service.diff(previous_observation, observation) if previous_observation else None
            previous_observation = observation

            # Episodic memory
            self.episodic_memory.record(
                session_id=run_id, step=step_number,
                observation_fingerprint=observation.fingerprint,
                action_taken="observe", result_success=True,
                url=observation.url, page_type=observation.page_type,
                workflow_state=workflow_state.value,
            )

            # ─── LOOP PREVENTION ───
            action_key = f"observe:{observation.fingerprint[:16]}"
            self.loop_analyzer.record_step(
                observation.fingerprint, observation.url,
                action_key, current_node.node_id,
                semantic_state=semantic_state,
            )
            loop_result = self.loop_analyzer.analyze()
            if loop_result.detected and loop_result.severity in {"high", "critical"}:
                self.slogger.warning(
                    "loop_detected", loop_type=loop_result.loop_type,
                    severity=loop_result.severity, step=step_number,
                )
                if loop_result.recommended_action == "reset_workflow":
                    run.status = "blocked"
                    run.summary = {"reason": f"Loop: {loop_result.description}"}
                    break

            # ─── PLAN ───
            self.reasoning_trace.start_decision(step_number)

            # Build skill context
            memory_refs = self.memory_retriever.retrieve_relevant(
                observation.url, observation.page_type, workflow_state.value,
            )

            active_objective = None
            if execution_plan:
                obj = execution_plan.get_active_objective()
                if obj:
                    subtask = obj.get_next_subtask()
                    active_objective = subtask.name if subtask else obj.name

            skill_context = SkillContext(
                goal=goal_type,
                workflow_state=workflow_state,
                observation=observation,
                page_classification=page_classification,
                form_analysis=form_analysis,
                auth_result=auth_result,
                auth_strategy=auth_strategy,
                credentials=credentials,
                visited_urls=list(memory.visited_urls),
                recent_failures=[
                    {"type": r.failure_type.value, "action": r.action.action.value}
                    for r in memory.results[-5:] if not r.success
                ],
                memory_hints=self.memory_retriever.compact_for_llm(
                    observation.url, observation.page_type, workflow_state.value,
                ),
                world_graph_summary=self.world_graph.compact_for_llm(),
                step_number=step_number,
                max_steps=max_steps,
                active_objective=active_objective,
            )

            # Try skill-based planning first
            decision = None
            if self._features.enable_skill_engine:
                decision = self.skill_router.selector.plan_with_skill(skill_context)

            # Fallback to legacy planner
            if decision is None:
                legacy_context = PlannerContext(
                    goal=goal_type, workflow_state=workflow_state,
                    observation=observation, memory=memory,
                    page=page_classification, form=form_analysis,
                    auth=auth_result, auth_strategy=auth_strategy, frontier=self.frontier,
                    credentials=credentials,
                )
                decision = self.legacy_planner.plan(legacy_context)

            action = decision.next_action
            memory.remember_action(action, step_number)
            await publish_event(
                ExecutionEventType.AGENT_REASONING,
                "Planning decision selected",
                confidence=decision.confidence,
                reasoning=decision.reasoning,
                action=action.model_dump(mode="json"),
            )
            await publish_event(
                ExecutionEventType.ACTION_EXECUTION,
                self.live_reasoning.narrate_action(action.model_dump(mode="json"), decision.reasoning[0] if decision.reasoning else ""),
                action=action.model_dump(mode="json"),
            )

            # ─── RISK ASSESSMENT ───
            risk = self.risk_engine.assess(action, observation)
            if not self.risk_engine.should_execute(risk):
                self.slogger.warning(
                    "action_blocked_by_risk", risk_score=risk.risk_score,
                    action=action.action.value, step=step_number,
                )
                run.status = "blocked"
                run.summary = {"reason": f"High risk action blocked: {risk.risk_factors}"}
                break

            # Finalize reasoning trace
            self.reasoning_trace.finalize_decision(
                step=step_number,
                selected_action=action.action.value,
                selected_skill=decision.selected_skill.skill_name if decision.selected_skill else decision.planner_name,
                confidence=decision.confidence,
                risk_score=risk.risk_score,
                candidate_count=len(decision.candidate_actions),
            )

            # ─── BUILD STEP ───
            step = AgentStep(
                step_number=step_number,
                observation=observation,
                workflow_state_before=workflow_before,
                workflow_state_after=workflow_state,
                planner_decision=decision,
                action=action,
                observation_diff=diff.model_dump(mode="json") if diff else None,
                skill_used=decision.selected_skill.skill_name if decision.selected_skill else None,
            )

            self.slogger.info(
                "planner_decision", step=step_number,
                planner=decision.planner_name,
                workflow_state=workflow_state.value,
                action=action.action.value,
                confidence=action.confidence,
                risk_score=risk.risk_score,
                skill=step.skill_used,
            )

            # Check completion
            if decision.completed:
                run.steps.append(step)
                run.status = "completed"
                break

            # ─── VALIDATE ───
            validation = self.validator.validate(action, observation, memory)
            step.validation = validation

            if not validation.valid:
                result = ActionResult(
                    success=False, action=action,
                    failure_type=validation.failure_type,
                    error=validation.reason,
                    before_url=observation.url, after_url=page.url,
                    before_fingerprint=observation.fingerprint,
                    after_fingerprint=observation.fingerprint,
                    recovery_hint="Replan using workflow state and memory.",
                )
                memory.remember_result(result, step_number)
                step.result = result
                run.steps.append(step)

                if validation.failure_type == FailureType.POLICY_BLOCKED:
                    run.status = "blocked"
                    break
                if memory.detects_loop():
                    run.status = "blocked"
                    run.summary = {"reason": "loop detected during validation"}
                    break
                continue

            # ─── EXECUTE ───
            exec_span = self.telemetry.start_span("action_execution")
            result = await self.executor.validated_execute(
                page=page, action=action, observation=observation,
                memory=memory, run_id=run_id, step=step_number,
                credentials=credentials, max_retries=max_retries_per_action,
                validation_engine=self.validator,
            )
            exec_duration = self.telemetry.end_span(exec_span)
            await publish_event(
                ExecutionEventType.TIMELINE_STEP,
                "Action execution completed",
                action=action.model_dump(mode="json"),
                duration_ms=exec_duration,
                success=result.success,
                failure_type=result.failure_type.value if not result.success else None,
            )

            # Post-execution observation
            await self.stability_service.wait_for_stable(page)
            refreshed = await self.observer.observe(page, run_id, step_number)
            refreshed_classification = self.page_classifier.classify(refreshed)
            refreshed.page_type = refreshed_classification.page_type
            refreshed_semantic_state = self.navigation_state.classify_state(
                refreshed, refreshed_classification, auth_result.authenticated,
            )
            post_workflow_state = self.navigation_state.resolve_workflow_state(
                workflow_state, refreshed, refreshed_classification, auth_result.authenticated,
            )
            transition = self.navigation_state.detect_transition(
                observation, refreshed, action, page_classification, refreshed_classification,
                workflow_before, post_workflow_state,
            )
            semantic_transitions.append(transition.model_dump(mode="json"))
            timeline_events.append({
                "type": "workflow_transition",
                "from": workflow_before.value,
                "to": workflow_state.value,
                "summary": transition.summary,
                "step": step_number,
            })
            await publish_event(
                ExecutionEventType.WORKFLOW_TRANSITION,
                self.live_reasoning.narrate_transition(workflow_before.value, workflow_state.value, transition.summary),
                from_state=workflow_before.value,
                to_state=workflow_state.value,
                transition=transition.model_dump(mode="json"),
            )
            workflow_state = post_workflow_state
            run.workflow_state = workflow_state
            memory.remember_transition(transition)
            result = self.outcome_validator.validate(action.expected_outcome, refreshed, result)
            memory.remember_result(result, step_number)
            step.result = result
            step.observation = refreshed
            step.observation_diff = self.diff_service.diff(observation, refreshed).model_dump(mode="json")
            step.navigation_transition = transition.model_dump(mode="json")
            step.semantic_state = refreshed_semantic_state
            step.workflow_state_after = workflow_state

            # ─── WORLD MODEL EDGE ───
            after_node = self.world_graph.add_or_update_node(
                url=refreshed.url,
                dom_fingerprint=refreshed.fingerprint,
                page_type=refreshed.page_type,
                workflow_state=workflow_state.value,
                parent_node_id=current_node.node_id,
            )
            self.world_graph.add_or_update_edge(
                source_node_id=current_node.node_id,
                target_node_id=after_node.node_id,
                action_type=action.action.value,
                selector=result.selector_used,
                target_label=action.target,
                success=result.success,
                latency_ms=result.duration_ms,
                skill_name=step.skill_used,
            )

            # ─── TRAJECTORY ───
            self.trajectory_engine.record_step(
                graph=self.world_graph,
                node_id=after_node.node_id,
                action_type=action.action.value,
                action_target=action.target,
                success=result.success,
                duration_ms=result.duration_ms,
                is_new_state=after_node.visit_count == 1,
            )

            # ─── EPISODIC MEMORY ───
            self.episodic_memory.record(
                session_id=run_id, step=step_number,
                observation_fingerprint=refreshed.fingerprint,
                action_taken=action.action.value,
                action_target=action.target,
                result_success=result.success,
                failure_type=result.failure_type.value if not result.success else None,
                url=refreshed.url, page_type=refreshed.page_type,
                workflow_state=workflow_state.value,
                duration_ms=result.duration_ms,
            )

            # ─── SEMANTIC LEARNING ───
            if result.success:
                self.semantic_memory.learn_pattern(
                    pattern_type="successful_action",
                    description=f"{action.action.value} on {observation.page_type}",
                    conditions={
                        "page_type": observation.page_type,
                        "action": action.action.value,
                        "url_pattern": observation.url.split("?")[0],
                    },
                    session_id=run_id,
                    success_rate=1.0,
                )
                if transition.semantic_change or transition.workflow_transition:
                    self.semantic_memory.learn_pattern(
                        pattern_type="navigation_transition",
                        description=transition.summary,
                        conditions={
                            "from_state": transition.from_state,
                            "to_state": transition.to_state,
                            "navigation_type": transition.navigation_type,
                        },
                        session_id=run_id,
                        success_rate=1.0,
                    )

            # ─── TELEMETRY ───
            self.telemetry.record_step(
                step=step_number, action=action.action.value,
                success=result.success, duration_ms=exec_duration,
                skill=step.skill_used, risk_score=risk.risk_score,
                confidence=action.confidence,
            )

            # ─── RECOVERY ───
            if not result.success:
                recovered_observation, recovery_results, recovery_decision = await self.recovery.recover(
                    page=page, failed_result=result,
                    observation=refreshed, memory=memory,
                    run_id=run_id, step=step_number, credentials=credentials,
                )
                step.recovery_actions = recovery_results
                step.recovery_decision = recovery_decision.model_dump(mode="json")
                for recovery_result in recovery_results:
                    memory.remember_result(recovery_result, step_number)
                step.observation = recovered_observation

                self.slogger.warning(
                    "recovery_executed", step=step_number,
                    strategy=recovery_decision.strategy,
                    reason=recovery_decision.reason,
                )
                await publish_event(
                    ExecutionEventType.BUG_DETECTED,
                    self.live_reasoning.narrate_issue(result.failure_type.value, result.error or recovery_decision.reason),
                    severity=result.failure_type.value,
                    failure_type=result.failure_type.value,
                    selector=result.selector_used,
                )
            run.steps.append(step)
            # Authentication memory tracking: capture auth attempts, signups, and session evidence
            try:
                act = step.action
                res = step.result
                if act and act.skill_name == "authenticate":
                    attempt = {
                        "type": "signup" if act.workflow_state == WorkflowState.SIGNUP_PAGE else "login",
                        "step": step_number,
                        "action": act.action.value,
                        "target": act.target,
                        "success": bool(res.success) if res is not None else False,
                        "reason": act.reason,
                    }
                    memory.remember_auth_attempt(attempt)
                    # Record created account when signup submit succeeds
                    if attempt["type"] == "signup" and res and res.success:
                        cred_snapshot = credentials or {}
                        memory.remember_account_created({"credentials": cred_snapshot, "step": step_number, "source": "generated" if cred_snapshot and cred_snapshot.get("source") == "generated" else "provided"})
                    # Record logout events heuristically
                    if act.action.value == ActionType.BACK.value and res and res.success and act.reason and "logout" in (act.reason or "").lower():
                        memory.remember_logout(True, step_number)
            except Exception:
                pass

            run.steps.append(step)
            run.artifacts.extend(result.artifacts)
            if step.skill_used and step.skill_used not in run.skills_used:
                run.skills_used.append(step.skill_used)

            # ─── OBJECTIVE EVALUATION ───
            goal_evaluation = self.goal_evaluator.evaluate(
                goal=goal,
                observation=refreshed,
                page_classification=refreshed_classification,
                transition=transition,
                workflow_state=workflow_state,
                authenticated=memory.authenticated or auth_result.authenticated,
            )
            goal_evaluations.append(goal_evaluation.model_dump(mode="json"))
            memory.remember_goal_completion(goal, goal_evaluation.goal_completed, goal_evaluation.confidence)
            if execution_plan and self._features.enable_objective_decomposition:
                obs_data = {
                    "url": refreshed.url, "title": refreshed.title,
                    "page_type": refreshed.page_type, "page_text": refreshed.page_text,
                }
                execution_plan.get_active_objective()
                active_obj = execution_plan.get_active_objective()
                if active_obj:
                    active_obj.evaluate_completion(obs_data)
            if goal_evaluation.goal_completed:
                run.status = "completed"
                step.goal_evaluation = goal_evaluation.model_dump(mode="json")
                run.steps[-1] = step
                break
            step.goal_evaluation = goal_evaluation.model_dump(mode="json")

            # Loop check
            if memory.detects_loop(
                semantic_change=transition.semantic_change,
                transition=transition,
                goal_completed=goal_evaluation.goal_completed,
                diff_changed=bool(step.observation_diff and step.observation_diff.get("semantic_change")),
            ):
                run.status = "blocked"
                run.summary = {"reason": "loop detected", "current_url": page.url}
                break

            if signals:
                signals.clear_transient()
        else:
            run.status = "max_steps_reached"

        # ─── FINALIZE ───
        if run.status == "running":
            run.status = "completed"

        trajectory = self.trajectory_engine.end_trajectory(success=run.status == "completed")
        run.trajectory_score = trajectory.total_reward

        run.completed_at = datetime.utcnow()
        run.memory_events = memory.events
        total_duration = int((time.perf_counter() - run_start_time) * 1000)

        runtime_steps = [step.model_dump(mode="json") for step in run.steps]
        performance_summary = analyze_performance(runtime_steps, run.summary)
        performance_findings.extend(performance_summary.get("findings", []))
        runtime_bug_cards = _runtime_bug_cards(runtime_steps)
        bug_clusters = cluster_bugs(runtime_bug_cards)

        run.summary |= {
            "visited_urls": len(memory.visited_urls),
            "steps": len(run.steps),
            "failures": len([r for r in memory.results if not r.success]),
            "artifacts": len(run.artifacts),
            "authenticated": memory.authenticated,
            "workflow_state": run.workflow_state.value,
            "frontier_remaining": len([
                c for c in self.frontier.state.discovered_routes.values() if not c.visited
            ]),
            "world_model_nodes": self.world_graph.node_count,
            "world_model_edges": self.world_graph.edge_count,
            "skills_used": run.skills_used,
            "trajectory_score": run.trajectory_score,
            "total_duration_ms": total_duration,
            "episodic_records": self.episodic_memory.total_records,
            "semantic_patterns": self.semantic_memory.total_patterns,
            "reasoning_decisions": self.reasoning_trace.total_decisions,
            "avg_confidence": round(self.reasoning_trace.avg_confidence, 3),
            "risk_stats": self.risk_engine.get_risk_stats(),
            "metrics": self.metrics.export(),
            "semantic_states": detected_semantic_states,
            "semantic_transitions": semantic_transitions,
            "goal_evaluations": goal_evaluations,
            "completed_goals": memory.completed_goals,
            "failed_goals": memory.failed_goals or ([] if run.status == "completed" else [goal]),
            "module_traversal_history": memory.module_traversal_history,
            "semantic_navigation_summary": self._semantic_navigation_summary(memory),
            "user_journey": self._user_journey(memory),
            "authentication_strategy": auth_strategy.strategy.value,
            "authentication_mode": auth_strategy.mode.value,
            "authentication_result": "SUCCESS" if memory.authenticated or auth_result.authenticated else "IN_PROGRESS",
            "authentication_confidence": round(auth_strategy.confidence, 3),
            "authentication_reasoning": auth_strategy.reasoning,
            "auth_route_type": auth_strategy.route.route_type.value if hasattr(auth_strategy.route.route_type, "value") else str(auth_strategy.route.route_type),
            "accessibility_findings": accessibility_findings,
            "performance_findings": performance_findings,
            "performance_summary": performance_summary,
            "bug_clusters": bug_clusters,
            "timeline_events": timeline_events,
        }

        if event_bus:
            await publish_event(
                ExecutionEventType.RUN_STATUS,
                "Agent run completed",
                status=run.status,
                workflow_state=run.workflow_state.value,
                performance_score=performance_summary.get("performance_score"),
            )

        run.current_url = page.url
        self.slogger.info(
            "agent_run_completed", status=run.status,
            steps=len(run.steps), duration_ms=total_duration,
            trajectory_score=run.trajectory_score,
        )
        return run

    @staticmethod
    def _goal_type(goal: str) -> GoalType:
        normalized = goal.lower().replace(" ", "_").replace("-", "_")
        for goal_type in GoalType:
            if goal_type.value in normalized:
                return goal_type
        if any(term in normalized for term in ["login", "sign_in", "auth"]):
            return GoalType.AUTHENTICATE_USER
        if "dashboard" in normalized:
            return GoalType.NAVIGATE_DASHBOARD
        if "form" in normalized or "submit" in normalized:
            return GoalType.SUBMIT_FORM
        if "regression" in normalized:
            return GoalType.RUN_REGRESSION
        return GoalType.VALIDATE_UI

    @staticmethod
    def _semantic_navigation_summary(memory: AgentMemory) -> str:
        if not memory.navigation_transitions:
            return "No semantic navigation transitions recorded."
        successful = [transition for transition in memory.successful_transitions if transition.summary]
        if successful:
            last = successful[-1]
            return (
                f"Observed {len(successful)} semantic transitions; latest was {last.summary}"
            )
        return f"Observed {len(memory.navigation_transitions)} navigation transitions with no confirmed semantic completion."

    @staticmethod
    def _user_journey(memory: AgentMemory) -> list[str]:
        journey = [transition.summary for transition in memory.successful_transitions if transition.summary]
        if journey:
            return journey[-12:]
        return memory.module_traversal_history[-12:]

    @staticmethod
    def _transition(current: WorkflowState, page_type: str, authenticated: bool) -> WorkflowState:
        if authenticated:
            return WorkflowState.AUTHENTICATED if page_type != "dashboard" else WorkflowState.DASHBOARD
        if page_type == "login_page":
            return WorkflowState.LOGIN_PAGE
        if page_type == "dashboard":
            return WorkflowState.DASHBOARD
        if page_type == "error_page":
            return WorkflowState.ERROR
        if page_type == "modal":
            return WorkflowState.MODAL_HANDLING
        if current == WorkflowState.INIT:
            return WorkflowState.LANDING_PAGE
        return current if current != WorkflowState.RECOVERY else WorkflowState.TESTING


def _runtime_bug_cards(steps: list[dict]) -> list[dict]:
    bug_cards: list[dict] = []
    for idx, step in enumerate(steps):
        result = step.get("result") or {}
        if not result or result.get("success", True):
            continue
        observation = step.get("observation") or {}
        failure_type = result.get("failure_type") or "unknown"
        workflow_stage = step.get("workflow_state_after") or observation.get("page_type") or "unknown"
        bug_cards.append(
            {
                "title": f"{failure_type.replace('_', ' ').title()} in {workflow_stage.replace('_', ' ').title()}",
                "severity": "critical" if failure_type in {"auth_failure", "session_expired", "policy_blocked"} else "high" if failure_type in {"navigation", "modal_blocked", "network_error"} else "medium",
                "description": result.get("error") or result.get("recovery_hint") or "Action failed",
                "technical_explanation": f"Observed failure type {failure_type} during {workflow_stage}.",
                "impact": f"The workflow is blocked at {workflow_stage}.",
                "confidence": 0.8,
                "workflow": "authentication" if any(term in str(workflow_stage) for term in ["login", "signup", "oauth", "forgot"]) else "workflow",
                "workflow_stage": workflow_stage,
                "affected_component": "authentication" if any(term in str(workflow_stage) for term in ["login", "signup", "oauth", "forgot"]) else "ui",
                "bug_type": failure_type,
                "root_cause": f"Failure type {failure_type} at {workflow_stage}",
                "reproduction_steps": [f"Re-run step {idx} targeting {result.get('selector_used') or step.get('action', {}).get('selector') or 'the observed control'}."],
                "expected_behavior": "The workflow should advance without failure.",
                "actual_behavior": result.get("error") or "Action failed",
                "screenshot_url": _runtime_screenshot_url(observation.get("screenshot")),
                "reproducible": True,
                "related_steps": [idx],
            }
        )
    return bug_cards


def _runtime_screenshot_url(screenshot: object) -> Optional[str]:
    if isinstance(screenshot, dict):
        path = screenshot.get("path")
        if path:
            normalized = str(path).replace("\\", "/")
            return "/" + normalized if not normalized.startswith("/") else normalized
    return None


async def run_agent_loop_v2(
    page: Page,
    goal: str,
    credentials: Optional[dict[str, str]] = None,
    start_url: Optional[str] = None,
    max_steps: int = 30,
    same_origin_only: bool = True,
    signals: Optional[BrowserSignals] = None,
    event_bus: Optional[ExecutionEventBus] = None,
    run_id: Optional[str] = None,
) -> dict:
    """
    Entry point for the upgraded agent loop.
    Drop-in replacement for the original run_agent_loop.
    """
    start = start_url or page.url
    policy = SafetyPolicy.from_start_url(start, same_origin_only=same_origin_only)
    loop = AutonomousAgentLoopV2(policy)
    run = await loop.run(
        page=page, start_url=start, goal=goal,
        credentials=credentials, max_steps=max_steps, signals=signals, event_bus=event_bus, run_id=run_id,
    )
    return run.model_dump(mode="json")
