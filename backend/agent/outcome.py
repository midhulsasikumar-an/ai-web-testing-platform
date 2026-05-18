from __future__ import annotations

from backend.core.models.actions import ActionResult
from backend.core.models.workflow import FailureType
from backend.core.models.observations import Observation


class OutcomeValidator:
    def validate(self, expected: str | None, observation: Observation, result: ActionResult) -> ActionResult:
        if not result.success or not expected:
            return result

        expected_lower = expected.lower()
        evidence = f"{observation.url} {observation.title} {observation.page_type} {observation.page_text}".lower()

        # Natural-language expectations stay permissive. Deterministic assertions should
        # be added as dedicated fields when product-specific goals are introduced.
        keywords = [word for word in expected_lower.replace("/", " ").split() if len(word) >= 5]
        if not keywords:
            return result
        if any(keyword in evidence for keyword in keywords):
            return result

        return result.model_copy(
            update={
                "success": False,
                "failure_type": FailureType.OUTCOME_MISMATCH,
                "error": f"Expected outcome not observed: {expected}",
                "recovery_hint": "Re-observe and replan because execution did not produce expected state.",
            }
        )
