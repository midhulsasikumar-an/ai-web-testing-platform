from __future__ import annotations

from typing import Any, Dict, List

from fastapi.encoders import jsonable_encoder

from backend.database.report_repository import save_report
from backend.multi_agent.models import AgentExecutionResult, UnifiedMultiAgentReport


def build_unified_report(
    *,
    run_id: str,
    user_id: str,
    goal: str,
    status: str,
    agent_results: List[AgentExecutionResult],
    consensus: Dict[str, Any],
    shared_memory: Dict[str, Any],
    navigation_graph: Dict[str, Any],
    workflow_coverage: Dict[str, Any],
) -> Dict[str, Any]:
    severity_prioritization = sorted(
        consensus.get("consensus_findings", []),
        key=lambda item: (-item.get("severity_rank", 0), -item.get("confidence", 0.0)),
    )
    reproduction_paths = _build_reproduction_paths(shared_memory, navigation_graph)
    report = UnifiedMultiAgentReport(
        run_id=run_id,
        user_id=user_id,
        test_run_id=run_id,
        report_type="multi_agent",
        title=goal,
        summary=str(consensus.get("summary") or consensus.get("verdict") or goal or "Multi-agent report").strip(),
        goal=goal,
        status=status,
        agent_results=[result.model_dump(mode="json") for result in agent_results],
        consensus=consensus,
        workflow_coverage=workflow_coverage,
        navigation_graph=navigation_graph,
        shared_memory=shared_memory,
        execution_map=navigation_graph,
        reproduction_paths=reproduction_paths,
        severity_prioritization=severity_prioritization,
    ).model_dump(mode="json")
    report_id = save_report(
        jsonable_encoder(report),
        report_type="multi_agent",
        user_id=user_id,
        test_run_id=run_id,
        title=goal,
        summary=report.get("summary") or goal,
        status=status,
    )
    report["report_id"] = report_id
    return report


def _build_reproduction_paths(shared_memory: Dict[str, Any], navigation_graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    paths: List[Dict[str, Any]] = []
    for path in shared_memory.get("navigation_paths", []):
        paths.append({
            "agent": path.get("agent"),
            "path": path,
            "source": "shared_memory",
        })
    for edge in navigation_graph.get("edges", []):
        paths.append({
            "agent": edge.get("agent_name"),
            "path": {
                "from": edge.get("from_node"),
                "to": edge.get("to_node"),
                "action": edge.get("action"),
                "url": edge.get("url"),
            },
            "source": "navigation_graph",
        })
    return paths
