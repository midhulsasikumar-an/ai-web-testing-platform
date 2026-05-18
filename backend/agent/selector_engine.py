from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from backend.core.models.observations import Observation, ObservedElement
from backend.core.models.actions import SelectorCandidate


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _css_escape(value: str) -> str:
    return re.sub(r"([^a-zA-Z0-9_-])", r"\\\1", value)


def _compact(value: Optional[str]) -> str:
    return " ".join((value or "").split()).strip()


@dataclass
class SelectorMemory:
    success_counts: dict[str, int] = field(default_factory=dict)
    failure_counts: dict[str, int] = field(default_factory=dict)

    def record_success(self, selector: str) -> None:
        self.success_counts[selector] = self.success_counts.get(selector, 0) + 1

    def record_failure(self, selector: str) -> None:
        self.failure_counts[selector] = self.failure_counts.get(selector, 0) + 1

    def score_adjustment(self, selector: str) -> float:
        successes = self.success_counts.get(selector, 0)
        failures = self.failure_counts.get(selector, 0)
        return float(successes * 3 - failures * 5)


class SelectorEngine:
    """Ranks stable selectors without exposing raw selector strings as the AI target."""

    def __init__(self, selector_memory: Optional[SelectorMemory] = None):
        self.selector_memory = selector_memory or SelectorMemory()

    def generate_candidates(self, raw: dict) -> List[SelectorCandidate]:
        candidates: List[SelectorCandidate] = []
        tag = _compact(raw.get("tag")).lower()
        role = _compact(raw.get("role")).lower()
        name = _compact(raw.get("accessible_name") or raw.get("aria_label") or raw.get("text"))
        data_testid = _compact(raw.get("data_testid"))
        aria_label = _compact(raw.get("aria_label"))
        element_id = _compact(raw.get("element_id"))
        input_name = _compact(raw.get("name"))
        placeholder = _compact(raw.get("placeholder"))
        text = _compact(raw.get("text"))

        if role and name:
            candidates.append(
                SelectorCandidate(
                    selector=f"{role}::{name}",
                    strategy="role",
                    score=100,
                    reason="accessibility role and accessible name",
                )
            )

        if data_testid:
            candidates.append(
                SelectorCandidate(
                    selector=f'[data-testid="{_quote(data_testid)}"]',
                    strategy="data-testid",
                    score=90,
                    reason="stable data-testid attribute",
                )
            )

        if aria_label:
            candidates.append(
                SelectorCandidate(
                    selector=f'[aria-label="{_quote(aria_label)}"]',
                    strategy="aria-label",
                    score=80,
                    reason="explicit aria label",
                )
            )

        if element_id and not self._looks_generated(element_id):
            candidates.append(
                SelectorCandidate(
                    selector=f"#{_css_escape(element_id)}",
                    strategy="id",
                    score=70,
                    reason="stable-looking id",
                )
            )

        if input_name:
            candidates.append(
                SelectorCandidate(
                    selector=f'[name="{_quote(input_name)}"]',
                    strategy="name",
                    score=65,
                    reason="form control name",
                )
            )

        if placeholder:
            candidates.append(
                SelectorCandidate(
                    selector=f'[placeholder="{_quote(placeholder)}"]',
                    strategy="placeholder",
                    score=55,
                    reason="input placeholder",
                )
            )

        if text and tag in {"button", "a"}:
            candidates.append(
                SelectorCandidate(
                    selector=f'text="{_quote(text)}"',
                    strategy="text",
                    score=45,
                    reason="visible semantic text",
                )
            )

        if tag:
            css = self._fallback_css(raw)
            if css:
                candidates.append(
                    SelectorCandidate(
                        selector=css,
                        strategy="css",
                        score=25,
                        reason="fallback CSS selector",
                    )
                )

        return self.rank_candidates(candidates)

    def rank_candidates(self, candidates: Iterable[SelectorCandidate]) -> List[SelectorCandidate]:
        ranked = []
        for candidate in candidates:
            adjusted = candidate.model_copy()
            adjusted.score = candidate.score + self.selector_memory.score_adjustment(candidate.selector)
            ranked.append(adjusted)
        return sorted(ranked, key=lambda item: item.score, reverse=True)

    def resolve_for_action(
        self,
        observation: Observation,
        element_index: Optional[int],
        target: Optional[str],
    ) -> Optional[ObservedElement]:
        if element_index is not None:
            for element in observation.elements:
                if element.index == element_index:
                    return element

        target_normalized = _compact(target).lower()
        if not target_normalized:
            return None

        matches = []
        for element in observation.elements:
            label = element.label.lower()
            if not label:
                continue
            if target_normalized == label:
                matches.append((100, element))
            elif label.startswith(target_normalized):
                matches.append((75, element))
            elif target_normalized in label:
                matches.append((50, element))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    @staticmethod
    def playwright_selector(candidate: SelectorCandidate) -> tuple[str, str]:
        if candidate.strategy == "role":
            role, _, name = candidate.selector.partition("::")
            return role, name
        return "selector", candidate.selector

    @staticmethod
    def _looks_generated(value: str) -> bool:
        lowered = value.lower()
        if len(value) > 40:
            return True
        if re.search(r"[0-9a-f]{8,}", lowered):
            return True
        return bool(re.search(r"(ember|react|radix|headlessui|mui)-?\d+", lowered))

    @staticmethod
    def _fallback_css(raw: dict) -> Optional[str]:
        tag = _compact(raw.get("tag")).lower()
        element_type = _compact(raw.get("element_type")).lower()
        class_name = _compact(raw.get("class_name"))
        if not tag:
            return None
        if element_type:
            return f'{tag}[type="{_quote(element_type)}"]'
        if class_name:
            first_class = class_name.split()[0]
            if first_class:
                return f"{tag}.{_css_escape(first_class)}"
        return tag
