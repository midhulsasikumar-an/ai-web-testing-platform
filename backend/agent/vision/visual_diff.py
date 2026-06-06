from __future__ import annotations

"""
Visual diff engine — compares screenshots to detect meaningful
visual changes between states.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent.vision.visual_diff")


class VisualDiffResult:
    """Result of comparing two visual states."""
    def __init__(
        self,
        change_score: float = 0.0,
        identical: bool = True,
        significant_change: bool = False,
        regions_changed: int = 0,
        change_description: str = "",
    ):
        self.change_score = change_score
        self.identical = identical
        self.significant_change = significant_change
        self.regions_changed = regions_changed
        self.change_description = change_description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_score": self.change_score,
            "identical": self.identical,
            "significant_change": self.significant_change,
            "regions_changed": self.regions_changed,
            "description": self.change_description,
        }


class VisualDiff:
    """
    Compares screenshots or visual states to detect meaningful changes.
    Uses file-level heuristics with hooks for future pixel-level comparison.
    """

    def __init__(self, significance_threshold: float = 0.1) -> None:
        self._threshold = significance_threshold

    def compare_screenshots(self, before_path: str, after_path: str) -> VisualDiffResult:
        """Compare two screenshot files for visual differences."""
        before = Path(before_path)
        after = Path(after_path)

        if not before.exists() or not after.exists():
            return VisualDiffResult(change_description="screenshot file(s) missing")

        before_hash = self._file_hash(before)
        after_hash = self._file_hash(after)

        if before_hash == after_hash:
            return VisualDiffResult(
                change_score=0.0, identical=True,
                change_description="screenshots are identical",
            )

        before_size = before.stat().st_size
        after_size = after.stat().st_size
        size_diff_ratio = abs(after_size - before_size) / max(before_size, 1)
        change_score = min(size_diff_ratio * 2 + 0.1, 1.0)

        descriptions = []
        if size_diff_ratio > 0.3:
            descriptions.append("major layout change")
        elif size_diff_ratio > 0.1:
            descriptions.append("moderate content change")
        else:
            descriptions.append("minor visual change")

        return VisualDiffResult(
            change_score=change_score,
            identical=False,
            significant_change=change_score > self._threshold,
            regions_changed=1 if change_score > self._threshold else 0,
            change_description=", ".join(descriptions),
        )

    def compare_fingerprints(self, before: str, after: str) -> VisualDiffResult:
        """Quick comparison using DOM fingerprints."""
        identical = before == after
        return VisualDiffResult(
            change_score=0.0 if identical else 0.5,
            identical=identical,
            significant_change=not identical,
            change_description="fingerprint match" if identical else "fingerprint changed",
        )

    @staticmethod
    def _file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:24]
