from __future__ import annotations

import re
from collections import Counter

from backend.core.models.semantic_state import ObservationDiff

from backend.core.models.observations import Observation


class ObservationDiffService:
    def diff(self, before: Observation, after: Observation) -> ObservationDiff:
        before_profile = self._profile(before)
        after_profile = self._profile(after)

        new_elements = sorted(set(after_profile["interactive_labels"]) - set(before_profile["interactive_labels"]))[:25]
        removed_elements = sorted(set(before_profile["interactive_labels"]) - set(after_profile["interactive_labels"]))[:25]

        heading_changed = before_profile["headings"] != after_profile["headings"]
        navigation_changed = before_profile["navigation_labels"] != after_profile["navigation_labels"]
        table_changed = before_profile["table_signature"] != after_profile["table_signature"]
        modal_changed = before_profile["modal_signature"] != after_profile["modal_signature"]
        form_changed = before_profile["form_signature"] != after_profile["form_signature"]
        visible_text_changed = before_profile["text_signature"] != after_profile["text_signature"]
        title_changed = before.title != after.title
        url_changed = before.url != after.url
        fingerprint_changed = before.fingerprint != after.fingerprint

        detected_changes: list[str] = []
        if url_changed:
            detected_changes.append("URL changed")
        if title_changed:
            detected_changes.append("title changed")
        if heading_changed:
            detected_changes.append("visible headings changed")
        if navigation_changed:
            detected_changes.append("navigation state changed")
        if table_changed:
            detected_changes.append("table/content region changed")
        if modal_changed:
            detected_changes.append("modal/dialog state changed")
        if form_changed:
            detected_changes.append("visible form state changed")
        if visible_text_changed:
            detected_changes.append("important text blocks changed")
        if new_elements:
            detected_changes.append(f"{len(new_elements)} new interactive elements")
        if removed_elements:
            detected_changes.append(f"{len(removed_elements)} removed interactive elements")

        semantic_change = any([
            heading_changed, navigation_changed, table_changed, modal_changed, form_changed, visible_text_changed,
        ])
        workflow_transition_detected = semantic_change or (url_changed and (title_changed or heading_changed))
        state_changed = url_changed or title_changed or semantic_change or fingerprint_changed
        confidence = self._confidence(
            url_changed=url_changed,
            title_changed=title_changed,
            heading_changed=heading_changed,
            navigation_changed=navigation_changed,
            table_changed=table_changed,
            modal_changed=modal_changed,
            form_changed=form_changed,
            visible_text_changed=visible_text_changed,
        )

        summary = ", ".join(detected_changes) if detected_changes else "no significant semantic state change"
        return ObservationDiff(
            state_changed=state_changed,
            semantic_change=semantic_change,
            url_changed=url_changed,
            title_changed=title_changed,
            heading_changed=heading_changed,
            navigation_changed=navigation_changed,
            table_changed=table_changed,
            modal_changed=modal_changed,
            form_changed=form_changed,
            workflow_transition_detected=workflow_transition_detected,
            confidence=confidence,
            summary=summary,
            detected_changes=detected_changes,
            fingerprint_changed=fingerprint_changed,
            new_elements=new_elements,
            removed_elements=removed_elements,
            visible_text_changed=visible_text_changed,
        )

    @staticmethod
    def _profile(observation: Observation) -> dict[str, object]:
        interactive_labels = [
            label
            for label in [
                *[heading.strip() for heading in observation.headings if heading.strip()],
                *[element.label.strip() for element in observation.elements if element.visible and element.label.strip()],
                *[form.get("name", "") for form in observation.forms if form.get("name")],
            ]
            if label
        ]
        navigation_labels = [
            label.lower()
            for label in interactive_labels
            if any(term in label.lower() for term in ["nav", "menu", "sidebar", "dashboard", "admin", "settings", "users", "profile", "reports", "analytics"])
        ]
        text_blocks = ObservationDiffService._text_blocks(observation.page_text)
        table_signature = ObservationDiffService._section_signature(
            text_blocks,
            include_terms=("table", "row", "column", "search", "filter", "page", "record", "users", "system"),
        )
        modal_signature = ObservationDiffService._section_signature(
            [*observation.dialogs, *interactive_labels],
            include_terms=("modal", "dialog", "popup", "overlay", "drawer"),
        )
        form_signature = ObservationDiffService._section_signature(
            [f"{form.get('name', '')} {form.get('method', '')} {form.get('action', '')}" for form in observation.forms],
            include_terms=("form", "input", "select", "submit", "login", "search", "filter"),
        )
        headings = tuple(h.strip().lower() for h in observation.headings if h.strip())
        return {
            "headings": headings,
            "navigation_labels": tuple(sorted(set(navigation_labels))),
            "table_signature": table_signature,
            "modal_signature": modal_signature,
            "form_signature": form_signature,
            "text_signature": ObservationDiffService._section_signature(text_blocks),
            "interactive_labels": tuple(sorted(set(label.lower() for label in interactive_labels))),
        }

    @staticmethod
    def _text_blocks(page_text: str, limit: int = 24) -> list[str]:
        raw_blocks = [block.strip() for block in re.split(r"[\n\r]+", page_text) if block.strip()]
        if not raw_blocks:
            raw_blocks = [page_text]
        blocks: list[str] = []
        for block in raw_blocks:
            normalized = " ".join(block.split()).lower()
            if len(normalized) < 12:
                continue
            blocks.append(normalized[:220])
        return blocks[:limit]

    @staticmethod
    def _section_signature(blocks: list[str], include_terms: tuple[str, ...] = ()) -> tuple[str, ...]:
        selected: list[str] = []
        for block in blocks:
            if include_terms and not any(term in block for term in include_terms):
                continue
            selected.append(block[:220])
        if not selected and blocks:
            selected.extend(blocks[:8])
        counter = Counter(selected)
        return tuple(sorted(f"{block}:{count}" for block, count in counter.items()))

    @staticmethod
    def _confidence(
        *,
        url_changed: bool,
        title_changed: bool,
        heading_changed: bool,
        navigation_changed: bool,
        table_changed: bool,
        modal_changed: bool,
        form_changed: bool,
        visible_text_changed: bool,
    ) -> float:
        score = 0.0
        score += 0.12 if url_changed else 0.0
        score += 0.12 if title_changed else 0.0
        score += 0.18 if heading_changed else 0.0
        score += 0.18 if navigation_changed else 0.0
        score += 0.14 if table_changed else 0.0
        score += 0.12 if modal_changed else 0.0
        score += 0.12 if form_changed else 0.0
        score += 0.12 if visible_text_changed else 0.0
        return min(score, 0.99)
