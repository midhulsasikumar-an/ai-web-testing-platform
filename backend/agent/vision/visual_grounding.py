from __future__ import annotations

"""
Visual grounding — maps visual elements to DOM elements,
performs coordinate mapping, and viewport prioritization.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.core.models.observations import ObservedElement, Observation
from backend.core.models.actions import BoundingBox

logger = logging.getLogger("agent.vision.visual_grounding")


class GroundedElement:
    """An element grounded in both DOM and visual space."""
    def __init__(
        self, element: ObservedElement,
        visual_x: float = 0, visual_y: float = 0,
        visual_confidence: float = 0.0,
        ocr_text: Optional[str] = None,
    ):
        self.element = element
        self.visual_x = visual_x
        self.visual_y = visual_y
        self.visual_confidence = visual_confidence
        self.ocr_text = ocr_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.element.index,
            "label": self.element.label,
            "visual_position": (self.visual_x, self.visual_y),
            "visual_confidence": self.visual_confidence,
            "ocr_text": self.ocr_text,
        }


class VisualGrounding:
    """
    Maps visual observations to DOM elements for multimodal reasoning.
    Provides coordinate mapping and viewport-aware element prioritization.
    """

    def __init__(self, viewport_width: int = 1365, viewport_height: int = 900) -> None:
        self._viewport_width = viewport_width
        self._viewport_height = viewport_height

    def ground_elements(self, observation: Observation) -> List[GroundedElement]:
        """Ground all visible elements with bbox in visual space."""
        grounded: List[GroundedElement] = []
        for element in observation.elements:
            if not element.visible or not element.bbox:
                continue
            center_x, center_y = element.bbox.center
            confidence = self._viewport_confidence(center_x, center_y, element.bbox)
            grounded.append(GroundedElement(
                element=element,
                visual_x=center_x,
                visual_y=center_y,
                visual_confidence=confidence,
            ))
        return sorted(grounded, key=lambda g: g.visual_confidence, reverse=True)

    def find_element_at_coordinates(
        self, observation: Observation, x: float, y: float, tolerance: float = 20.0,
    ) -> Optional[ObservedElement]:
        """Find the DOM element at specific visual coordinates."""
        best_match: Optional[ObservedElement] = None
        best_distance = float("inf")
        for element in observation.elements:
            if not element.bbox or not element.visible:
                continue
            bbox = element.bbox
            if bbox.x <= x <= bbox.x + bbox.width and bbox.y <= y <= bbox.y + bbox.height:
                cx, cy = bbox.center
                dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                if dist < best_distance:
                    best_distance = dist
                    best_match = element
        if best_match is None and tolerance > 0:
            for element in observation.elements:
                if not element.bbox or not element.visible:
                    continue
                cx, cy = element.bbox.center
                dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                if dist <= tolerance and dist < best_distance:
                    best_distance = dist
                    best_match = element
        return best_match

    def get_viewport_elements(self, observation: Observation) -> List[ObservedElement]:
        """Get elements currently visible in the viewport."""
        viewport = []
        scroll_y = observation.scroll.get("y", 0)
        for element in observation.elements:
            if not element.bbox or not element.visible:
                continue
            elem_y = element.bbox.y
            if elem_y >= scroll_y and elem_y <= scroll_y + self._viewport_height:
                viewport.append(element)
        return viewport

    def prioritize_for_action(self, observation: Observation) -> List[ObservedElement]:
        """Prioritize elements for interaction based on visual position and size."""
        grounded = self.ground_elements(observation)
        prioritized = []
        for g in grounded:
            el = g.element
            if not el.enabled:
                continue
            score = g.visual_confidence
            if el.role in {"button", "link", "textbox"}:
                score += 0.2
            if el.bbox and el.bbox.area > 500:
                score += 0.1
            prioritized.append((score, el))
        prioritized.sort(key=lambda x: x[0], reverse=True)
        return [el for _, el in prioritized]

    def _viewport_confidence(self, x: float, y: float, bbox: BoundingBox) -> float:
        """Score element by how centered it is in the viewport."""
        center_x_ratio = abs(x - self._viewport_width / 2) / (self._viewport_width / 2)
        center_y_ratio = abs(y - self._viewport_height / 2) / (self._viewport_height / 2)
        position_score = 1.0 - (center_x_ratio + center_y_ratio) / 2
        size_score = min(bbox.area / 10000, 1.0)
        return max(position_score * 0.7 + size_score * 0.3, 0.0)
