from __future__ import annotations

"""
Benchmark framework — tracks success rates, recovery rates, latency,
token usage, navigation efficiency, planner accuracy, and failure categories.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BenchmarkResult(BaseModel):
    """Result of a single benchmark run."""
    benchmark_name: str
    scenario: str
    success: bool
    steps_taken: int = 0
    max_steps: int = 30
    duration_ms: int = 0
    recovery_count: int = 0
    failures: List[str] = Field(default_factory=list)
    skills_used: List[str] = Field(default_factory=list)
    token_usage: int = 0
    urls_visited: int = 0
    final_workflow_state: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BenchmarkSuite:
    """Base benchmark suite with metrics tracking and reporting."""

    def __init__(self, name: str, output_dir: str = "data/benchmarks") -> None:
        self.name = name
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._results: List[BenchmarkResult] = []

    def record(self, result: BenchmarkResult) -> None:
        self._results.append(result)

    @property
    def success_rate(self) -> float:
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if r.success) / len(self._results)

    @property
    def avg_steps(self) -> float:
        if not self._results:
            return 0.0
        return sum(r.steps_taken for r in self._results) / len(self._results)

    @property
    def avg_duration_ms(self) -> float:
        if not self._results:
            return 0.0
        return sum(r.duration_ms for r in self._results) / len(self._results)

    @property
    def recovery_rate(self) -> float:
        failed = [r for r in self._results if r.recovery_count > 0]
        if not failed:
            return 0.0
        recovered = sum(1 for r in failed if r.success)
        return recovered / len(failed)

    def failure_categories(self) -> Dict[str, int]:
        categories: Dict[str, int] = {}
        for result in self._results:
            for f in result.failures:
                categories[f] = categories.get(f, 0) + 1
        return dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))

    def skill_usage(self) -> Dict[str, int]:
        usage: Dict[str, int] = {}
        for result in self._results:
            for s in result.skills_used:
                usage[s] = usage.get(s, 0) + 1
        return usage

    def report(self) -> Dict[str, Any]:
        return {
            "benchmark": self.name,
            "total_runs": len(self._results),
            "success_rate": round(self.success_rate, 4),
            "avg_steps": round(self.avg_steps, 1),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "recovery_rate": round(self.recovery_rate, 4),
            "failure_categories": self.failure_categories(),
            "skill_usage": self.skill_usage(),
            "total_tokens": sum(r.token_usage for r in self._results),
        }

    def save_report(self) -> str:
        report = self.report()
        report["generated_at"] = datetime.utcnow().isoformat()
        path = self._output_dir / f"{self.name}_{int(time.time())}.json"
        path.write_text(json.dumps(report, indent=2, default=str))
        return str(path)


class LoginBenchmark(BenchmarkSuite):
    """Benchmark for login/authentication workflows."""
    def __init__(self) -> None:
        super().__init__("login_benchmark")

    def create_scenario(self, url: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        return {
            "benchmark": self.name, "scenario": "authenticate_user",
            "url": url, "goal": "authenticate_user", "credentials": credentials,
            "expected_outcome": "dashboard",
        }


class NavigationBenchmark(BenchmarkSuite):
    """Benchmark for navigation and exploration workflows."""
    def __init__(self) -> None:
        super().__init__("navigation_benchmark")

    def create_scenario(self, url: str, target_pages: List[str]) -> Dict[str, Any]:
        return {
            "benchmark": self.name, "scenario": "explore_navigation",
            "url": url, "goal": "explore_navigation",
            "expected_pages_visited": target_pages,
        }


class RecoveryBenchmark(BenchmarkSuite):
    """Benchmark for failure recovery capabilities."""
    def __init__(self) -> None:
        super().__init__("recovery_benchmark")


class ModalBenchmark(BenchmarkSuite):
    """Benchmark for modal/overlay handling."""
    def __init__(self) -> None:
        super().__init__("modal_benchmark")


class RegressionBenchmark(BenchmarkSuite):
    """Benchmark for regression testing workflows."""
    def __init__(self) -> None:
        super().__init__("regression_benchmark")


class BenchmarkRunner:
    """Runs and aggregates all benchmark suites."""

    def __init__(self) -> None:
        self.suites: Dict[str, BenchmarkSuite] = {
            "login": LoginBenchmark(),
            "navigation": NavigationBenchmark(),
            "recovery": RecoveryBenchmark(),
            "modal": ModalBenchmark(),
            "regression": RegressionBenchmark(),
        }

    def record_result(self, suite_name: str, result: BenchmarkResult) -> None:
        suite = self.suites.get(suite_name)
        if suite:
            suite.record(result)

    def full_report(self) -> Dict[str, Any]:
        return {
            name: suite.report()
            for name, suite in self.suites.items()
        }

    def save_all_reports(self) -> List[str]:
        return [suite.save_report() for suite in self.suites.values() if suite._results]
