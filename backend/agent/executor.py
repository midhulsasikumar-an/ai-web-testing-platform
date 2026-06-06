from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from backend.agent.memory_service import AgentMemory
from backend.agent.safety import SafetyPolicy
from backend.core.models.actions import ActionResult, AgentAction, BrowserArtifact, SelectorCandidate
from backend.core.models.workflow import ActionType, FailureType
from backend.core.models.observations import Observation, ObservedElement
from backend.agent.selector_engine import SelectorEngine
from backend.agent.validator.action_validator import ActionValidationEngine, ActionValidationResult


class ActionExecutor:
    def __init__(
        self,
        selector_engine: SelectorEngine,
        safety_policy: SafetyPolicy,
        artifacts_root: str = "screenshots",
        timeout_ms: int = 10000,
    ):
        self.selector_engine = selector_engine
        self.safety_policy = safety_policy
        self.artifacts_root = Path(artifacts_root)
        self.timeout_ms = timeout_ms

    async def execute(
        self,
        page: Page,
        action: AgentAction,
        observation: Observation,
        memory: AgentMemory,
        run_id: str,
        step: int,
        credentials: Optional[dict[str, str]] = None,
        max_retries: int = 2,
    ) -> ActionResult:
        started = time.perf_counter()
        artifacts: list[BrowserArtifact] = []
        before_artifact = await self._screenshot(page, run_id, step, "before")
        if before_artifact:
            artifacts.append(before_artifact)

        selector_used: Optional[str] = None
        retries = 0
        before_url = page.url
        failure_type = FailureType.UNKNOWN
        error: Optional[str] = None

        try:
            if action.action == ActionType.NAVIGATE:
                if not action.url:
                    raise AgentExecutionError(FailureType.INVALID_ACTION, "Navigate action has no url")
                await self._safe_goto(page, observation.url, action.url)
                return self._result(
                    True,
                    action,
                    before_url,
                    page.url,
                    observation.fingerprint,
                    "",
                    started,
                    artifacts,
                    selector_used,
                    retries,
                )

            if action.action == ActionType.BACK:
                await page.go_back(wait_until="domcontentloaded", timeout=self.timeout_ms)
                return self._result(
                    True,
                    action,
                    before_url,
                    page.url,
                    observation.fingerprint,
                    "",
                    started,
                    artifacts,
                    selector_used,
                    retries,
                )

            if action.action == ActionType.WAIT:
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
                return self._result(
                    True,
                    action,
                    before_url,
                    page.url,
                    observation.fingerprint,
                    observation.fingerprint,
                    started,
                    artifacts,
                    selector_used,
                    retries,
                )

            if action.action == ActionType.SCROLL:
                await page.mouse.wheel(0, int(action.value or "700"))
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
                return self._result(
                    True,
                    action,
                    before_url,
                    page.url,
                    observation.fingerprint,
                    "",
                    started,
                    artifacts,
                    selector_used,
                    retries,
                )

            element = self.selector_engine.resolve_for_action(
                observation,
                action.element_index,
                action.target,
            )
            if not element:
                raise AgentExecutionError(FailureType.SELECTOR_NOT_FOUND, "No observed element matches action")

            candidates = self.selector_engine.rank_candidates(element.selector_candidates)
            if action.selector:
                candidates = sorted(
                    candidates,
                    key=lambda candidate: candidate.selector != action.selector,
                )
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                retries = attempt
                for candidate in candidates:
                    try:
                        locator = self._locator(page, candidate)
                        await self._execute_on_locator(page, locator, action, credentials)
                        selector_used = candidate.selector
                        after_artifact = await self._screenshot(page, run_id, step, "after")
                        if after_artifact:
                            artifacts.append(after_artifact)
                        return self._result(
                            True,
                            action,
                            before_url,
                            page.url,
                            observation.fingerprint,
                            "",
                            started,
                            artifacts,
                            selector_used,
                            retries,
                        )
                    except Exception as exc:
                        last_exception = exc
                        self.selector_engine.selector_memory.record_failure(candidate.selector)
                        await self._small_recovery(page, element)

            failure_type = self._classify_exception(last_exception)
            error = str(last_exception) if last_exception else "No selector candidates worked"
            selector_used = candidates[0].selector if candidates else None

        except AgentExecutionError as exc:
            failure_type = exc.failure_type
            error = exc.message
        except PlaywrightTimeoutError as exc:
            failure_type = FailureType.TIMEOUT
            error = str(exc)
        except PlaywrightError as exc:
            failure_type = self._classify_exception(exc)
            error = str(exc)
        except Exception as exc:
            failure_type = FailureType.UNKNOWN
            error = str(exc)

        after_artifact = await self._screenshot(page, run_id, step, "after_failure")
        if after_artifact:
            artifacts.append(after_artifact)
        return self._result(
            False,
            action,
            before_url,
            page.url,
            observation.fingerprint,
            "",
            started,
            artifacts,
            selector_used,
            retries,
            failure_type=failure_type,
            error=error,
            recovery_hint=self._recovery_hint(failure_type),
        )

    async def validated_execute(
        self,
        page: Page,
        action: AgentAction,
        observation: Observation,
        memory: AgentMemory,
        run_id: str,
        step: int,
        credentials: Optional[dict[str, str]] = None,
        max_retries: int = 2,
        validation_engine: ActionValidationEngine | None = None,
    ) -> ActionResult:
        engine = validation_engine or ActionValidationEngine(SafetyPolicy.from_start_url(observation.url))
        result: ActionValidationResult = engine.validate(action, observation, memory)
        if not result.valid:
            return self._result(
                False,
                action,
                page.url,
                page.url,
                observation.fingerprint,
                observation.fingerprint,
                time.perf_counter(),
                [],
                None,
                0,
                failure_type=result.failure_type or FailureType.INVALID_ACTION,
                error=result.reason,
                recovery_hint="Action validation failed",
            )
        return await self.execute(
            page=page,
            action=action,
            observation=observation,
            memory=memory,
            run_id=run_id,
            step=step,
            credentials=credentials,
            max_retries=max_retries,
        )

    async def _execute_on_locator(
        self,
        page: Page,
        locator: Locator,
        action: AgentAction,
        credentials: Optional[dict[str, str]],
    ) -> None:
        await locator.first.wait_for(state="visible", timeout=self.timeout_ms)
        await locator.first.scroll_into_view_if_needed(timeout=self.timeout_ms)

        if action.action in {ActionType.CLICK, ActionType.SUBMIT}:
            await locator.first.click(timeout=self.timeout_ms)
            await self._settle_after_action(page)
            return

        if action.action == ActionType.HOVER:
            await locator.first.hover(timeout=self.timeout_ms)
            return

        if action.action == ActionType.FILL:
            value = self._resolve_value(action.value or "", credentials)
            await locator.first.fill(value, timeout=self.timeout_ms)
            return

        if action.action == ActionType.SELECT:
            await locator.first.select_option(value=action.value or "", timeout=self.timeout_ms)
            return

        raise AgentExecutionError(FailureType.INVALID_ACTION, f"Unsupported element action: {action.action.value}")

    async def _safe_goto(self, page: Page, current_url: str, target_url: str) -> None:
        normalized = urljoin(current_url, target_url)
        safety = self.safety_policy.validate_navigation(current_url, normalized)
        if not safety.valid:
            raise AgentExecutionError(FailureType.POLICY_BLOCKED, safety.reason)
        await page.goto(normalized, wait_until="domcontentloaded", timeout=15000)

    async def _settle_after_action(self, page: Page) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=2500)
        except Exception:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=2500)
            except Exception:
                pass

    async def _small_recovery(self, page: Page, element: ObservedElement) -> None:
        if element.bbox:
            await page.mouse.wheel(0, 400)
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass

    def _locator(self, page: Page, candidate: SelectorCandidate) -> Locator:
        if candidate.strategy == "role":
            role, _, name = candidate.selector.partition("::")
            return page.get_by_role(role, name=name)
        return page.locator(candidate.selector)

    async def _screenshot(
        self,
        page: Page,
        run_id: str,
        step: int,
        label: str,
    ) -> Optional[BrowserArtifact]:
        folder = self.artifacts_root / run_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"step_{step:03d}_{label}.png"
        try:
            await page.screenshot(path=str(path), full_page=False)
            return BrowserArtifact(artifact_type="screenshot", path=str(path), label=label)
        except Exception:
            return None

    @staticmethod
    def _resolve_value(value: str, credentials: Optional[dict[str, str]]) -> str:
        if value.startswith("{") and value.endswith("}") and credentials:
            key = value.strip("{} ").strip()
            return credentials.get(key, value)
        return value

    @staticmethod
    def _classify_exception(exc: Optional[Exception]) -> FailureType:
        if exc is None:
            return FailureType.UNKNOWN
        text = str(exc).lower()
        if "timeout" in text:
            return FailureType.TIMEOUT
        if "detached" in text or "not attached" in text:
            return FailureType.DETACHED
        if "navigation" in text:
            return FailureType.NAVIGATION
        if "strict mode violation" in text or "selector" in text:
            return FailureType.SELECTOR_NOT_FOUND
        if "dialog" in text or "modal" in text:
            return FailureType.MODAL_BLOCKED
        return FailureType.EXECUTION

    @staticmethod
    def _recovery_hint(failure_type: FailureType) -> str:
        return {
            FailureType.SELECTOR_NOT_FOUND: "Re-observe the page and repair selector from indexed elements.",
            FailureType.TIMEOUT: "Wait for page stability, retry once, then replan.",
            FailureType.DETACHED: "DOM changed; re-observe before retrying.",
            FailureType.MODAL_BLOCKED: "Dismiss modal or cookie banner before retrying.",
            FailureType.NAVIGATION: "Backtrack or choose another frontier URL.",
        }.get(failure_type, "Re-observe and ask planner for an alternative action.")

    @staticmethod
    def _result(
        success: bool,
        action: AgentAction,
        before_url: str,
        after_url: str,
        before_fingerprint: str,
        after_fingerprint: str,
        started: float,
        artifacts: list[BrowserArtifact],
        selector_used: Optional[str],
        retries: int,
        failure_type: FailureType = FailureType.NONE,
        error: Optional[str] = None,
        recovery_hint: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ActionResult:
        return ActionResult(
            success=success,
            action=action,
            failure_type=failure_type,
            error=error,
            selector_used=selector_used,
            before_url=before_url,
            after_url=after_url,
            before_fingerprint=before_fingerprint,
            after_fingerprint=after_fingerprint,
            duration_ms=int((time.perf_counter() - started) * 1000),
            retries=retries,
            artifacts=artifacts,
            recovery_hint=recovery_hint,
            metadata=metadata or {},
        )


class AgentExecutionError(Exception):
    def __init__(self, failure_type: FailureType, message: str):
        super().__init__(message)
        self.failure_type = failure_type
        self.message = message
