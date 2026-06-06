from __future__ import annotations

"""
Graph memory — persistence and retrieval layer for the world graph.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agent.world_model.navigation_edge import NavigationEdge
from backend.agent.world_model.navigation_node import NavigationNode
from backend.agent.world_model.world_graph import WorldGraph

logger = logging.getLogger("agent.world_model.graph_memory")


class GraphMemory:
    """Persistence and retrieval layer for the world-state graph."""

    def __init__(self, persistence_dir: str = "data/world_model") -> None:
        self._persistence_dir = Path(persistence_dir)
        self._persistence_dir.mkdir(parents=True, exist_ok=True)

    def save_graph(self, graph: WorldGraph, session_id: str) -> str:
        file_path = self._persistence_dir / f"graph_{session_id}.json"
        data = graph.export_graph()
        data["session_id"] = session_id
        data["saved_at"] = datetime.utcnow().isoformat()
        file_path.write_text(json.dumps(data, indent=2, default=str))
        return str(file_path)

    def load_graph(self, session_id: str) -> Optional[WorldGraph]:
        file_path = self._persistence_dir / f"graph_{session_id}.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text())
            graph = WorldGraph()
            for node_data in data.get("nodes", {}).values():
                node = NavigationNode(**node_data)
                graph._nodes[node.node_id] = node
                url_pattern = node.url.split("?")[0].split("#")[0]
                graph._node_url_index[url_pattern].add(node.node_id)
            for edge_data in data.get("edges", {}).values():
                edge = NavigationEdge(**edge_data)
                graph._edges[edge.edge_id] = edge
                graph._adjacency[edge.source_node_id].append(edge.edge_id)
                graph._reverse_adjacency[edge.target_node_id].append(edge.edge_id)
            graph._current_node_id = data.get("current_node_id")
            return graph
        except Exception as exc:
            logger.error("graph_load_failed", extra={"error": str(exc)})
            return None

    def merge_graphs(self, graphs: List[WorldGraph]) -> WorldGraph:
        merged = WorldGraph()
        for graph in graphs:
            for node_id, node in graph._nodes.items():
                existing = merged._nodes.get(node_id)
                if existing:
                    existing.visit_count += node.visit_count
                    existing.success_actions += node.success_actions
                    existing.failed_actions += node.failed_actions
                else:
                    merged._nodes[node_id] = node.model_copy()
                    url_pattern = node.url.split("?")[0].split("#")[0]
                    merged._node_url_index[url_pattern].add(node_id)
            for edge_id, edge in graph._edges.items():
                existing = merged._edges.get(edge_id)
                if existing:
                    existing.execution_count += edge.execution_count
                    existing.success_count += edge.success_count
                    existing.failure_count += edge.failure_count
                else:
                    merged._edges[edge_id] = edge.model_copy()
                    merged._adjacency[edge.source_node_id].append(edge_id)
                    merged._reverse_adjacency[edge.target_node_id].append(edge_id)
        return merged

    def extract_navigation_patterns(self, graph: WorldGraph, min_success_rate: float = 0.8) -> List[Dict[str, Any]]:
        patterns: List[Dict[str, Any]] = []
        for edge in graph._edges.values():
            if edge.success_rate >= min_success_rate and edge.execution_count >= 2:
                source = graph.get_node(edge.source_node_id)
                target = graph.get_node(edge.target_node_id)
                if source and target:
                    patterns.append({
                        "source_page_type": source.page_type,
                        "target_page_type": target.page_type,
                        "action_type": edge.action_type,
                        "selector": edge.selector,
                        "success_rate": edge.success_rate,
                        "confidence": edge.reliability_score,
                    })
        return sorted(patterns, key=lambda p: p["confidence"], reverse=True)
