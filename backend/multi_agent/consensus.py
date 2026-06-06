from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding
from backend.services.bug_clustering_service import cluster_bugs


class ConsensusValidationEngine:
    def validate(self, agent_results: List[AgentExecutionResult]) -> Dict[str, Any]:
        bug_cards: List[Dict[str, Any]] = []
        for result in agent_results:
            for finding in result.findings:
                bug_cards.append(self._to_bug_card(result.agent_name, finding))

        clusters = cluster_bugs(bug_cards)
        root_causes: List[Dict[str, Any]] = []
        for cluster in clusters:
            root_causes.append(self._derive_root_cause(cluster, bug_cards))

        agent_signals: Dict[str, List[str]] = defaultdict(list)
        for card in bug_cards:
            agent_signals[card["agent"]].append(card["category"])

        consensus_findings = sorted(
            root_causes,
            key=lambda item: (-item.get("confidence", 0.0), item.get("severity_rank", 0)),
        )

        return {
            "bug_cards": bug_cards,
            "clusters": clusters,
            "consensus_findings": consensus_findings,
            "agent_signals": dict(agent_signals),
            "severity_counts": dict(Counter(card["severity"] for card in bug_cards)),
        }

    @staticmethod
    def _to_bug_card(agent_name: str, finding: MultiAgentFinding) -> Dict[str, Any]:
        return {
            "agent": agent_name,
            "category": finding.category,
            "severity": finding.severity,
            "message": finding.message,
            "root_cause": finding.root_cause or finding.category,
            "technical_explanation": finding.evidence.get("technical_explanation") or finding.message,
            "affected_component": finding.evidence.get("affected_component") or finding.workflow_state or finding.category,
            "workflow_stage": finding.workflow_state or "unknown",
            "url": finding.url,
            "evidence": finding.evidence,
            "confidence": finding.confidence,
        }

    @staticmethod
    def _derive_root_cause(cluster: Dict[str, Any], bug_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        bugs = cluster.get("bugs", [])
        messages = " ".join(str(item.get("message", "")).lower() for item in bugs)
        categories = {str(item.get("category", "")).lower() for item in bugs}
        agents = sorted({str(item.get("agent", "")) for item in bugs if item.get("agent")})
        severity = str(cluster.get("severity", "low"))

        root_cause = cluster.get("root_cause", "unknown")
        confidence = 0.55

        if any(term in messages for term in ["api", "latency", "timeout", "failed request"]) and any(term in messages for term in ["render", "blank", "ui", "visual"]):
            root_cause = "API degradation causing downstream rendering failure"
            confidence = 0.9
        elif any(term in messages for term in ["auth", "login", "session"]) and any(term in messages for term in ["navigation", "dashboard", "admin"]):
            root_cause = "Authentication or session state corruption"
            confidence = 0.85
        elif "accessibility" in categories and any(term in messages for term in ["form", "label", "aria"]):
            root_cause = "Inaccessible form controls"
            confidence = 0.8

        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 1)
        return {
            "root_cause": root_cause,
            "severity": severity,
            "severity_rank": severity_rank,
            "confidence": confidence,
            "affected_agents": agents,
            "supporting_bugs": bugs,
        }
