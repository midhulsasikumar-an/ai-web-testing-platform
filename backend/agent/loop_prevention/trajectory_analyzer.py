"""
Advanced loop prevention — stagnation detection, cyclic navigation
detection, trajectory entropy analysis, and recovery escalation.
"""

from __future__ import annotations

import math
import logging
from collections import Counter, deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent.loop_prevention")


class LoopDetectionResult:
    """Result of loop/stagnation analysis."""
    def __init__(
        self, detected: bool = False, loop_type: str = "none",
        severity: str = "none", description: str = "",
        recommended_action: str = "continue",
    ):
        self.detected = detected
        self.loop_type = loop_type
        self.severity = severity
        self.description = description
        self.recommended_action = recommended_action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected, "type": self.loop_type,
            "severity": self.severity, "description": self.description,
            "recommended_action": self.recommended_action,
        }


class StagnationDetector:
    """Detects when the agent is stuck without making progress."""

    def __init__(self, window_size: int = 8) -> None:
        self._fingerprint_history: deque[str] = deque(maxlen=window_size * 2)
        self._url_history: deque[str] = deque(maxlen=window_size * 2)
        self._action_history: deque[str] = deque(maxlen=window_size)
        self._semantic_history: deque[str] = deque(maxlen=window_size * 2)
        self._transition_history: deque[str] = deque(maxlen=window_size)
        self._window = window_size

    def record(self, fingerprint: str, url: str, action_key: str, semantic_state: str = "", transition_key: str = "") -> None:
        self._fingerprint_history.append(fingerprint)
        self._url_history.append(url)
        self._action_history.append(action_key)
        if semantic_state:
            self._semantic_history.append(semantic_state)
        if transition_key:
            self._transition_history.append(transition_key)

    def detect(self) -> LoopDetectionResult:
        # URL oscillation: ping-ponging between 2 URLs
        if len(self._url_history) >= 6:
            recent_urls = list(self._url_history)[-6:]
            if len(set(recent_urls)) <= 2:
                recent_semantic = list(self._semantic_history)[-6:] if self._semantic_history else []
                recent_transitions = list(self._transition_history)[-6:] if self._transition_history else []
                semantic_diversity = len(set(recent_semantic)) if recent_semantic else 0
                transition_diversity = len(set(recent_transitions)) if recent_transitions else 0
                if semantic_diversity <= 1 and transition_diversity <= 1:
                    return LoopDetectionResult(
                        detected=True, loop_type="url_oscillation", severity="high",
                        description=f"Oscillating between {len(set(recent_urls))} URLs without semantic progress",
                        recommended_action="reset_workflow",
                    )

        # Fingerprint stagnation: same page state repeated
        if len(self._fingerprint_history) >= 4:
            recent = list(self._fingerprint_history)[-4:]
            recent_semantic = list(self._semantic_history)[-4:] if self._semantic_history else []
            if len(set(recent)) == 1 and (not recent_semantic or len(set(recent_semantic)) == 1):
                return LoopDetectionResult(
                    detected=True, loop_type="fingerprint_stagnation", severity="high",
                    description="Same page fingerprint for 4 consecutive steps",
                    recommended_action="switch_skill",
                )

        # Action repetition: same action repeated
        if len(self._action_history) == self._action_history.maxlen:
            recent_semantic = list(self._semantic_history)[-self._action_history.maxlen:] if self._semantic_history else []
            if len(set(self._action_history)) <= 2 and (not recent_semantic or len(set(recent_semantic)) <= 1):
                return LoopDetectionResult(
                    detected=True, loop_type="action_repetition", severity="medium",
                    description="Repetitive action pattern detected",
                    recommended_action="replan",
                )

        return LoopDetectionResult()


class CyclicNavigationDetector:
    """Detects cyclic navigation patterns (A→B→C→A)."""

    def __init__(self, max_cycle_length: int = 6) -> None:
        self._path_history: List[str] = []
        self._max_cycle = max_cycle_length

    def record(self, node_id: str) -> None:
        self._path_history.append(node_id)

    def detect(self) -> LoopDetectionResult:
        if len(self._path_history) < 4:
            return LoopDetectionResult()

        for cycle_len in range(2, min(self._max_cycle + 1, len(self._path_history) // 2 + 1)):
            recent = self._path_history[-cycle_len:]
            previous = self._path_history[-2 * cycle_len:-cycle_len]
            if recent == previous:
                return LoopDetectionResult(
                    detected=True, loop_type="cyclic_navigation",
                    severity="high" if cycle_len <= 3 else "medium",
                    description=f"Navigation cycle of length {cycle_len} detected",
                    recommended_action="reset_workflow" if cycle_len <= 3 else "switch_skill",
                )

        return LoopDetectionResult()


class EntropyTracker:
    """Tracks entropy of agent behavior to detect monotonous patterns."""

    def __init__(self, window_size: int = 12) -> None:
        self._action_window: deque[str] = deque(maxlen=window_size)
        self._entropy_history: List[float] = []

    def record(self, action_key: str) -> None:
        self._action_window.append(action_key)
        if len(self._action_window) >= 4:
            self._entropy_history.append(self._calculate_entropy())

    def detect_low_entropy(self, threshold: float = 0.5) -> LoopDetectionResult:
        if len(self._entropy_history) < 3:
            return LoopDetectionResult()

        recent_entropy = sum(self._entropy_history[-3:]) / 3
        if recent_entropy < threshold:
            return LoopDetectionResult(
                detected=True, loop_type="low_entropy", severity="medium",
                description=f"Low action diversity (entropy: {recent_entropy:.2f})",
                recommended_action="switch_skill",
            )
        return LoopDetectionResult()

    def _calculate_entropy(self) -> float:
        if not self._action_window:
            return 0.0
        counts = Counter(self._action_window)
        total = len(self._action_window)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(total) if total > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    @property
    def current_entropy(self) -> float:
        return self._entropy_history[-1] if self._entropy_history else 1.0


class TrajectoryAnalyzer:
    """Combines all loop detection subsystems into unified analysis."""

    def __init__(self) -> None:
        self.stagnation = StagnationDetector()
        self.cyclic = CyclicNavigationDetector()
        self.entropy = EntropyTracker()

    def record_step(self, fingerprint: str, url: str, action_key: str, node_id: str = "", semantic_state: str = "", transition_key: str = "") -> None:
        self.stagnation.record(fingerprint, url, action_key, semantic_state=semantic_state, transition_key=transition_key)
        self.cyclic.record(node_id or fingerprint[:16])
        self.entropy.record(action_key)

    def analyze(self) -> LoopDetectionResult:
        """Run all detectors and return the most severe result."""
        results = [
            self.stagnation.detect(),
            self.cyclic.detect(),
            self.entropy.detect_low_entropy(),
        ]
        detected = [r for r in results if r.detected]
        if not detected:
            return LoopDetectionResult()

        severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return max(detected, key=lambda r: severity_order.get(r.severity, 0))
