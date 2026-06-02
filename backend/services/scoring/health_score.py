from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple


CRITICAL_FEATURE_KEYS = {"LOGIN", "CHECKOUT", "PAYMENT", "CART", "AUTH", "AUTHENTICATION", "INVENTORY"}


def _normalize_status(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_pass_status(value: Any) -> bool:
    return _normalize_status(value) in {"pass", "passed", "completed", "success"}


def _is_failure_status(value: Any) -> bool:
    return _normalize_status(value) in {"fail", "failed", "error"}


def _is_critical_objective(objective: Dict[str, Any]) -> bool:
    feature_key = str(objective.get("feature_key") or "").strip().upper()
    coverage_level = str(objective.get("coverage_level") or "").strip().upper()
    priority_score = int(objective.get("priority_score", 0) or 0)
    risk_score = int(objective.get("risk_score", 0) or 0)
    explicit = bool(objective.get("critical") or objective.get("is_critical"))
    return explicit or coverage_level == "SECURITY" or feature_key in CRITICAL_FEATURE_KEYS or priority_score >= 4 or risk_score >= 75


def _build_objective_rows(results: Iterable[Dict[str, Any]], objective_coverage: List[Dict[str, Any]] | None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if objective_coverage:
        normalized_rows: List[Dict[str, Any]] = []
        scenario_rows: List[Dict[str, Any]] = []
        for objective in objective_coverage:
            objective_status = str(objective.get("execution_status") or "").strip().lower()
            failed_scenarios = int(objective.get("failed_scenarios", 0) or 0)
            passed_scenarios = int(objective.get("passed_scenarios", 0) or 0)
            executed_scenarios = int(objective.get("executed_scenarios", 0) or passed_scenarios + failed_scenarios)
            generated_scenarios = int(objective.get("generated_scenarios", executed_scenarios) or executed_scenarios)
            normalized_rows.append(
                {
                    "objective_id": objective.get("objective_id"),
                    "objective_name": objective.get("objective_name"),
                    "feature_key": objective.get("feature_key"),
                    "coverage_level": objective.get("coverage_level"),
                    "priority_score": int(objective.get("priority_score", 0) or 0),
                    "risk_score": int(objective.get("risk_score", objective.get("priority_score", 0)) or 0),
                    "executed_scenarios": executed_scenarios,
                    "passed_scenarios": passed_scenarios,
                    "failed_scenarios": failed_scenarios,
                    "generated_scenarios": generated_scenarios,
                    "execution_status": "passed" if objective_status in {"completed", "passed", "pass"} and failed_scenarios == 0 else "failed",
                    "critical": _is_critical_objective(objective),
                }
            )
            scenario_rows.extend(list(objective.get("scenarios", []) or []))
        return normalized_rows, scenario_rows

    grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "objective_id": "",
        "objective_name": "",
        "feature_key": "",
        "coverage_level": "",
        "priority_score": 0,
        "executed_scenarios": 0,
        "passed_scenarios": 0,
        "failed_scenarios": 0,
        "generated_scenarios": 0,
        "execution_status": "passed",
        "critical": False,
    })
    scenario_rows: List[Dict[str, Any]] = []
    saw_objective_metadata = False

    for result in results or []:
        if not isinstance(result, dict):
            continue
        objective_id = str(result.get("objective_id") or "").strip()
        if not objective_id:
            continue
        saw_objective_metadata = True
        row = grouped[objective_id]
        row["objective_id"] = objective_id
        row["objective_name"] = row["objective_name"] or result.get("objective_name") or objective_id
        row["feature_key"] = row["feature_key"] or result.get("feature_key") or ""
        row["coverage_level"] = row["coverage_level"] or result.get("coverage_level") or ""
        row["priority_score"] = max(int(row.get("priority_score", 0) or 0), int(result.get("priority_score", 0) or 0))
        row["executed_scenarios"] += 1
        row["generated_scenarios"] += 1
        if _is_pass_status(result.get("status")):
            row["passed_scenarios"] += 1
        elif _is_failure_status(result.get("status")):
            row["failed_scenarios"] += 1
        row["critical"] = row["critical"] or _is_critical_objective(row)
        scenario_rows.append(result)

    normalized_rows = list(grouped.values())
    if saw_objective_metadata:
        for row in normalized_rows:
            row["execution_status"] = "passed" if row["failed_scenarios"] == 0 and row["executed_scenarios"] > 0 else "failed"
        return normalized_rows, scenario_rows

    return [], []


def calculate_health_score(results, objective_coverage=None):
    results = list(results or [])
    objective_rows, scenario_rows = _build_objective_rows(results, list(objective_coverage or []))

    if objective_rows:
        total_objectives = len(objective_rows)
        passed_objectives = sum(1 for row in objective_rows if row["execution_status"] == "passed")
        failed_objectives = total_objectives - passed_objectives
        critical_objective_failures = sum(1 for row in objective_rows if row["execution_status"] == "failed" and row.get("critical"))
        risk_weighted_failures = sum(max(1, int(row.get("risk_score", 0) or 0) // 25) for row in objective_rows if row["execution_status"] == "failed")

        total_scenarios = sum(int(row.get("executed_scenarios", 0) or 0) for row in objective_rows)
        passed_scenarios = sum(int(row.get("passed_scenarios", 0) or 0) for row in objective_rows)
        failed_scenarios = sum(int(row.get("failed_scenarios", 0) or 0) for row in objective_rows)

        objective_pass_rate = round((passed_objectives / total_objectives), 4) if total_objectives else 0.0
        scenario_pass_rate = round((passed_scenarios / total_scenarios), 4) if total_scenarios else 0.0

        coverage_score = round(min(100.0, (objective_pass_rate * 60.0) + (scenario_pass_rate * 40.0)), 2)
        critical_penalty = min(45.0, critical_objective_failures * 15.0)
        noncritical_penalty = min(20.0, max(0, failed_objectives - critical_objective_failures) * 5.0)
        risk_penalty = min(25.0, float(risk_weighted_failures) * 2.5)
        health_score = round(max(0.0, coverage_score - critical_penalty - noncritical_penalty - risk_penalty), 2)

        breadth_factor = min(0.3, total_objectives / (total_objectives + 4.0) * 0.15 + total_scenarios / (total_scenarios + 8.0) * 0.15)
        confidence_score = round(min(0.99, 0.5 + breadth_factor + (0.08 if critical_objective_failures == 0 else 0.0)), 2)

        summary = {
            "total": total_objectives,
            "passed": passed_objectives,
            "failed": failed_objectives,
            "info": 0,
            "total_objectives": total_objectives,
            "passed_objectives": passed_objectives,
            "failed_objectives": failed_objectives,
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "objective_pass_rate": objective_pass_rate,
            "scenario_pass_rate": scenario_pass_rate,
            "critical_objective_failures": critical_objective_failures,
            "risk_weighted_failures": risk_weighted_failures,
            "coverage_score": coverage_score,
            "health_score": health_score,
            "confidence_score": confidence_score,
        }

        return {
            "score": health_score,
            "health_score": health_score,
            "coverage_score": coverage_score,
            "confidence_score": confidence_score,
            "objective_pass_rate": objective_pass_rate,
            "scenario_pass_rate": scenario_pass_rate,
            "critical_objective_failures": critical_objective_failures,
            "risk_weighted_failures": risk_weighted_failures,
            "summary": summary,
        }

    if not results:
        return {
            "score": 0,
            "health_score": 0,
            "coverage_score": 0,
            "confidence_score": 0,
            "objective_pass_rate": 0,
            "scenario_pass_rate": 0,
            "critical_objective_failures": 0,
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "info": 0,
                "total_objectives": 0,
                "passed_objectives": 0,
                "failed_objectives": 0,
                "total_scenarios": 0,
                "passed_scenarios": 0,
                "failed_scenarios": 0,
                "objective_pass_rate": 0,
                "scenario_pass_rate": 0,
                "critical_objective_failures": 0,
                "coverage_score": 0,
                "health_score": 0,
                "confidence_score": 0,
            },
        }

    score = 0
    total = len(results) * 10

    for r in results:
        if _is_pass_status(r.get("status")):
            score += 10
        elif _normalize_status(r.get("status")) == "info":
            score += 5

    percentage = int((score / total) * 100) if total else 0

    return {
        "score": percentage,
        "health_score": percentage,
        "coverage_score": percentage,
        "confidence_score": 0.5,
        "objective_pass_rate": 0,
        "scenario_pass_rate": 0,
        "critical_objective_failures": 0,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if _is_pass_status(r.get("status"))),
            "failed": sum(1 for r in results if _is_failure_status(r.get("status"))),
            "info": sum(1 for r in results if _normalize_status(r.get("status")) == "info"),
        },
    }