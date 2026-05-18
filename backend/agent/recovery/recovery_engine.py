from __future__ import annotations

from pydantic import BaseModel
from playwright.async_api import Page

from backend.agent.executor import ActionExecutor
from backend.agent.memory_service import AgentMemory
from backend.agent.observer import BrowserObserver
from backend.core.models.actions import ActionResult, AgentAction
from backend.core.models.workflow import ActionType, FailureType, WorkflowState
from backend.core.models.observations import Observation


class RecoveryDecision(BaseModel):
    strategy: str
    reason: str
    retry_original: bool = False
    exhausted: bool = False


class RecoveryEngine:
    def __init__(self, observer: BrowserObserver, executor: ActionExecutor):
        self.observer = observer
        self.executor = executor

    def decide(self, failed_result: ActionResult, memory: AgentMemory) -> RecoveryDecision:
        if memory.detects_loop():
            return RecoveryDecision(
                strategy="restart_workflow_stage",
                reason="Loop prevention triggered by repeated state/action pattern",
                exhausted=False,
            )
        if failed_result.failure_type == FailureType.SELECTOR_NOT_FOUND:
            return RecoveryDecision(
                strategy="retry_with_alternate_selector",
                reason="Selector failed; re-observe and retry with repaired selector candidates",
                retry_original=True,
            )
        if failed_result.failure_type in {FailureType.TIMEOUT, FailureType.DETACHED}:
            return RecoveryDecision(
                strategy="wait_for_network_idle",
                reason="DOM or navigation timing instability detected",
                retry_original=True,
            )
        if failed_result.failure_type == FailureType.MODAL_BLOCKED:
            return RecoveryDecision(
                strategy="dismiss_modal",
                reason="Modal or dialog appears to block execution",
                retry_original=True,
            )
        if failed_result.failure_type == FailureType.NAVIGATION:
            return RecoveryDecision(
                strategy="refresh_page",
                reason="Navigation failed or reached unstable state",
                retry_original=False,
            )
        return RecoveryDecision(
            strategy="replan",
            reason="Failure is not safely recoverable by local executor",
            exhausted=True,
        )

    async def recover(
        self,
        page: Page,
        failed_result: ActionResult,
        observation: Observation,
        memory: AgentMemory,
        run_id: str,
        step: int,
        credentials: dict[str, str] | None = None,
    ) -> tuple[Observation, list[ActionResult], RecoveryDecision]:
        decision = self.decide(failed_result, memory)
        recovery_results: list[ActionResult] = []

        if decision.strategy == "dismiss_modal":
            await self._dismiss_modal(page)

        elif decision.strategy == "wait_for_network_idle":
            await self._wait_for_stability(page)

        elif decision.strategy == "retry_with_alternate_selector":
            await page.mouse.wheel(0, 500)
            await self._wait_for_stability(page)

        elif decision.strategy == "refresh_page":
            try:
                await page.reload(wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass

        elif decision.strategy == "restart_workflow_stage":
            try:
                await page.goto(memory.visited_sequence[0], wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass

        refreshed = await self.observer.observe(page, run_id, step)

        if decision.retry_original and not decision.exhausted:
            retry_result = await self.executor.validated_execute(
                page=page,
                action=failed_result.action,
                observation=refreshed,
                memory=memory,
                run_id=run_id,
                step=step,
                credentials=credentials,
                max_retries=1,
            )
            recovery_results.append(retry_result)
            refreshed = await self.observer.observe(page, run_id, step)

        return refreshed, recovery_results, decision

    async def _dismiss_modal(self, page: Page) -> None:
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        for label in ["Close", "Cancel", "No thanks", "Accept", "Got it"]:
            try:
                button = page.get_by_role("button", name=label)
                if await button.count() > 0:
                    await button.first.click(timeout=1500)
                    return
            except Exception:
                continue

    async def _wait_for_stability(self, page: Page) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass
