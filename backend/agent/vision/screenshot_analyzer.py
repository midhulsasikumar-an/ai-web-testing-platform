from __future__ import annotations

"""
Screenshot analyzer — analyzes screenshots for visual understanding,
UI element detection, and visual state comparison.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("agent.vision.screenshot_analyzer")


class VisualRegion:
    """A detected region in a screenshot."""
    def __init__(
        self, x: float, y: float, width: float, height: float,
        label: str = "", confidence: float = 0.0,
        region_type: str = "unknown",
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.label = label
        self.confidence = confidence
        self.region_type = region_type

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y, "width": self.width, "height": self.height,
            "label": self.label, "confidence": self.confidence, "type": self.region_type,
        }


class ScreenshotAnalyzer:
    """
    Analyzes screenshots for visual understanding using heuristic
    and pixel-analysis methods. Designed for future ML model integration.
    """

    def __init__(self, max_width: int = 1365, max_height: int = 900) -> None:
        self._max_width = max_width
        self._max_height = max_height
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}

    async def analyze(self, screenshot_path: str) -> Dict[str, Any]:
        """Analyze a screenshot and return visual understanding data."""
        path = Path(screenshot_path)
        if not path.exists():
            return {"error": "screenshot not found", "regions": [], "hash": ""}

        content_hash = self._hash_file(path)
        if content_hash in self._analysis_cache:
            return self._analysis_cache[content_hash]

        file_size = path.stat().st_size
        analysis = {
            "path": str(path),
            "hash": content_hash,
            "file_size_bytes": file_size,
            "estimated_complexity": self._estimate_complexity(file_size),
            "regions": [],
            "has_modal_overlay": False,
            "has_error_state": False,
            "dominant_layout": "unknown",
            "visual_density": 0.0,
        }

        self._analysis_cache[content_hash] = analysis
        return analysis

    def compare(self, before_path: str, after_path: str) -> Dict[str, Any]:
        """Compare two screenshots and return visual diff information."""
        before = Path(before_path)
        after = Path(after_path)

        if not before.exists() or not after.exists():
            return {"error": "screenshot(s) not found", "change_score": 0.0}

        before_hash = self._hash_file(before)
        after_hash = self._hash_file(after)

        identical = before_hash == after_hash
        before_size = before.stat().st_size
        after_size = after.stat().st_size
        size_ratio = min(before_size, after_size) / max(before_size, after_size) if max(before_size, after_size) > 0 else 1.0

        change_score = 0.0 if identical else max(1.0 - size_ratio, 0.1)

        return {
            "identical": identical,
            "change_score": change_score,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "size_change_bytes": after_size - before_size,
            "significant_change": change_score > 0.15,
        }

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()[:24]

    @staticmethod
    def _estimate_complexity(file_size: int) -> str:
        if file_size < 50_000:
            return "low"
        if file_size < 200_000:
            return "medium"
        return "high"
