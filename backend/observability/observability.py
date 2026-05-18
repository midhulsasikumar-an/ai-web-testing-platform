"""
Enterprise observability — structured logging, metrics collection,
execution telemetry, and distributed tracing for the agent platform.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("observability")


class StructuredLogger:
    """JSON-structured logger for all agent subsystem events."""

    def __init__(self, name: str = "agent", level: str = "INFO") -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._context: Dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        self._context.update(kwargs)

    def clear_context(self) -> None:
        self._context.clear()

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        data = {**self._context, **kwargs, "event": event, "timestamp": datetime.utcnow().isoformat()}
        self._logger.log(level, json.dumps(data, default=str))

    def info(self, event: str, **kwargs: Any) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, **kwargs)


class MetricsCollector:
    """Collects and aggregates agent execution metrics."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._started_at = time.time()

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def histogram(self, name: str, value: float) -> None:
        self._histograms[name].append(value)

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0}
        sorted_vals = sorted(values)
        return {
            "count": len(values),
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": sum(values) / len(values),
            "p50": sorted_vals[len(sorted_vals) // 2],
            "p95": sorted_vals[int(len(sorted_vals) * 0.95)] if len(sorted_vals) >= 20 else sorted_vals[-1],
        }

    def export(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram_stats(k) for k in self._histograms},
            "uptime_seconds": time.time() - self._started_at,
        }


class ExecutionTelemetry:
    """Tracks execution-level telemetry for agent runs."""

    def __init__(self, metrics: MetricsCollector) -> None:
        self._metrics = metrics
        self._active_spans: Dict[str, float] = {}

    def start_span(self, name: str) -> str:
        span_id = f"{name}_{uuid.uuid4().hex[:8]}"
        self._active_spans[span_id] = time.perf_counter()
        return span_id

    def end_span(self, span_id: str) -> float:
        start = self._active_spans.pop(span_id, None)
        if start is None:
            return 0.0
        duration_ms = (time.perf_counter() - start) * 1000
        name = span_id.rsplit("_", 1)[0]
        self._metrics.histogram(f"span.{name}.duration_ms", duration_ms)
        return duration_ms

    def record_step(
        self, step: int, action: str, success: bool,
        duration_ms: float, skill: Optional[str] = None,
        risk_score: float = 0.0, confidence: float = 0.0,
    ) -> None:
        self._metrics.increment("steps.total")
        self._metrics.increment(f"steps.{'success' if success else 'failure'}")
        self._metrics.histogram("step.duration_ms", duration_ms)
        self._metrics.histogram("step.confidence", confidence)
        self._metrics.histogram("step.risk_score", risk_score)
        if skill:
            self._metrics.increment(f"skill.{skill}.invocations")

    def record_browser_event(self, event_type: str) -> None:
        self._metrics.increment(f"browser.{event_type}")

    def record_token_usage(self, tokens: int) -> None:
        self._metrics.increment("tokens.total", tokens)
        self._metrics.histogram("tokens.per_call", float(tokens))


class DistributedTrace:
    """Distributed tracing for cross-service correlation."""

    def __init__(self) -> None:
        self._traces: Dict[str, List[Dict[str, Any]]] = {}

    def start_trace(self, trace_id: Optional[str] = None) -> str:
        tid = trace_id or str(uuid.uuid4())[:16]
        self._traces[tid] = []
        return tid

    def add_span(
        self, trace_id: str, service: str, operation: str,
        duration_ms: float, metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if trace_id in self._traces:
            self._traces[trace_id].append({
                "span_id": str(uuid.uuid4())[:8],
                "service": service,
                "operation": operation,
                "duration_ms": duration_ms,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            })

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        return self._traces.get(trace_id, [])

    def export_traces(self) -> Dict[str, List[Dict[str, Any]]]:
        return dict(self._traces)
