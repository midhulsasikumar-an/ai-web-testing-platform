"""
World graph — the core navigation graph data structure that maintains
the full world-state graph with nodes (states) and edges (transitions).
Supports graph search, path optimization, and stagnation analysis.
"""

from __future__ import annotations

import heapq
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.agent.world_model.navigation_edge import NavigationEdge
from backend.agent.world_model.navigation_node import NavigationNode


class WorldGraph:
    """
    A directed graph of application states and action-based transitions.

    This is the agent's internal model of the web application's navigation
    structure, built incrementally as the agent explores.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, NavigationNode] = {}
        self._edges: Dict[str, NavigationEdge] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)  # node_id -> [edge_ids]
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)  # node_id -> [incoming edge_ids]
        self._current_node_id: Optional[str] = None
        self._node_url_index: Dict[str, Set[str]] = defaultdict(set)  # url_pattern -> {node_ids}

    @property
    def current_node(self) -> Optional[NavigationNode]:
        if self._current_node_id and self._current_node_id in self._nodes:
            return self._nodes[self._current_node_id]
        return None

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def get_node(self, node_id: str) -> Optional[NavigationNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[NavigationEdge]:
        return self._edges.get(edge_id)

    def add_or_update_node(
        self,
        url: str,
        dom_fingerprint: str,
        page_type: str,
        workflow_state: str = "",
        semantic_labels: Optional[List[str]] = None,
        screenshot_hash: Optional[str] = None,
        headings: Optional[List[str]] = None,
        form_count: int = 0,
        interactive_element_count: int = 0,
        parent_node_id: Optional[str] = None,
        duration_ms: int = 0,
    ) -> NavigationNode:
        """Add a new node or update an existing one. Returns the node."""
        node_id = NavigationNode.generate_node_id(url, dom_fingerprint, page_type)
        url_pattern = url.split("?")[0].split("#")[0]

        existing = self._nodes.get(node_id)
        if existing:
            existing.update_visit(duration_ms)
            if screenshot_hash:
                existing.screenshot_hash = screenshot_hash
            if semantic_labels:
                for label in semantic_labels:
                    if label not in existing.semantic_labels:
                        existing.semantic_labels.append(label)
            self._current_node_id = node_id
            return existing

        depth = 0
        if parent_node_id and parent_node_id in self._nodes:
            depth = self._nodes[parent_node_id].depth + 1

        node = NavigationNode(
            node_id=node_id,
            url=url,
            url_pattern=url_pattern,
            page_type=page_type,
            dom_fingerprint=dom_fingerprint,
            semantic_labels=semantic_labels or [],
            screenshot_hash=screenshot_hash,
            workflow_state=workflow_state,
            headings=headings or [],
            form_count=form_count,
            interactive_element_count=interactive_element_count,
            visit_count=1,
            parent_node_id=parent_node_id,
            depth=depth,
            is_error_state=page_type in {"error_page", "404", "500"},
        )
        self._nodes[node_id] = node
        self._node_url_index[url_pattern].add(node_id)
        self._current_node_id = node_id
        return node

    def add_or_update_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        action_type: str,
        selector: Optional[str] = None,
        target_label: Optional[str] = None,
        action_value: Optional[str] = None,
        success: bool = True,
        latency_ms: float = 0.0,
        skill_name: Optional[str] = None,
    ) -> NavigationEdge:
        """Add a new edge or update an existing one. Returns the edge."""
        edge_id = NavigationEdge.generate_edge_id(
            source_node_id, target_node_id, action_type, selector
        )

        existing = self._edges.get(edge_id)
        if existing:
            existing.record_execution(success, latency_ms)
            return existing

        edge = NavigationEdge(
            edge_id=edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            action_type=action_type,
            selector=selector,
            target_label=target_label,
            action_value=action_value,
            skill_name=skill_name,
            execution_count=1,
            success_count=1 if success else 0,
            failure_count=0 if success else 1,
            avg_latency_ms=latency_ms,
            total_latency_ms=latency_ms,
            transition_confidence=1.0 if success else 0.0,
        )
        self._edges[edge_id] = edge
        self._adjacency[source_node_id].append(edge_id)
        self._reverse_adjacency[target_node_id].append(edge_id)
        return edge

    def get_outgoing_edges(self, node_id: str) -> List[NavigationEdge]:
        """Get all outgoing edges from a node."""
        return [
            self._edges[eid]
            for eid in self._adjacency.get(node_id, [])
            if eid in self._edges
        ]

    def get_incoming_edges(self, node_id: str) -> List[NavigationEdge]:
        """Get all incoming edges to a node."""
        return [
            self._edges[eid]
            for eid in self._reverse_adjacency.get(node_id, [])
            if eid in self._edges
        ]

    def get_neighbors(self, node_id: str) -> List[NavigationNode]:
        """Get all nodes reachable from the given node."""
        neighbors = []
        for edge_id in self._adjacency.get(node_id, []):
            edge = self._edges.get(edge_id)
            if edge and edge.target_node_id in self._nodes:
                neighbors.append(self._nodes[edge.target_node_id])
        return neighbors

    def shortest_path(
        self,
        start_node_id: str,
        end_node_id: str,
        weight: str = "latency",
    ) -> Optional[List[str]]:
        """
        Dijkstra's shortest path between two nodes.
        Weight can be 'latency', 'hops', or 'reliability'.
        """
        if start_node_id not in self._nodes or end_node_id not in self._nodes:
            return None

        distances: Dict[str, float] = {start_node_id: 0.0}
        predecessors: Dict[str, str] = {}
        heap: List[Tuple[float, str]] = [(0.0, start_node_id)]
        visited: Set[str] = set()

        while heap:
            dist, current = heapq.heappop(heap)
            if current in visited:
                continue
            visited.add(current)

            if current == end_node_id:
                path = []
                node = end_node_id
                while node in predecessors:
                    path.append(node)
                    node = predecessors[node]
                path.append(start_node_id)
                return list(reversed(path))

            for edge_id in self._adjacency.get(current, []):
                edge = self._edges.get(edge_id)
                if not edge or edge.target_node_id in visited:
                    continue

                if weight == "latency":
                    edge_weight = edge.avg_latency_ms if edge.avg_latency_ms > 0 else 1000.0
                elif weight == "reliability":
                    edge_weight = 1.0 / max(edge.reliability_score, 0.01)
                else:
                    edge_weight = 1.0

                new_dist = dist + edge_weight
                if new_dist < distances.get(edge.target_node_id, float("inf")):
                    distances[edge.target_node_id] = new_dist
                    predecessors[edge.target_node_id] = current
                    heapq.heappush(heap, (new_dist, edge.target_node_id))

        return None

    def find_nodes_by_page_type(self, page_type: str) -> List[NavigationNode]:
        """Find all nodes matching a page type."""
        return [
            node for node in self._nodes.values()
            if node.page_type == page_type
        ]

    def find_nodes_by_url_pattern(self, url_pattern: str) -> List[NavigationNode]:
        """Find all nodes matching a URL pattern."""
        return [
            self._nodes[nid]
            for nid in self._node_url_index.get(url_pattern, set())
            if nid in self._nodes
        ]

    def get_stagnation_hotspots(self, threshold: float = 3.0) -> List[NavigationNode]:
        """Find nodes with high revisitation and low success."""
        return sorted(
            [n for n in self._nodes.values() if n.revisitation_score >= threshold],
            key=lambda n: n.revisitation_score,
            reverse=True,
        )

    def get_dead_ends(self) -> List[NavigationNode]:
        """Find nodes with no outgoing edges."""
        return [
            node for node_id, node in self._nodes.items()
            if not self._adjacency.get(node_id) and not node.is_terminal
        ]

    def get_failed_paths(self) -> List[NavigationEdge]:
        """Get edges with high failure rates."""
        return sorted(
            [e for e in self._edges.values() if e.failure_count > 0],
            key=lambda e: e.failure_count,
            reverse=True,
        )

    def get_successful_paths(self, min_success_rate: float = 0.8) -> List[NavigationEdge]:
        """Get edges with high success rates."""
        return [
            e for e in self._edges.values()
            if e.success_rate >= min_success_rate and e.execution_count >= 2
        ]

    def bfs_reachable(self, start_node_id: str, max_depth: int = 10) -> List[NavigationNode]:
        """BFS to find all reachable nodes from start within max_depth."""
        if start_node_id not in self._nodes:
            return []

        visited: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque([(start_node_id, 0)])
        reachable: List[NavigationNode] = []

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)
            reachable.append(self._nodes[node_id])

            for edge_id in self._adjacency.get(node_id, []):
                edge = self._edges.get(edge_id)
                if edge and edge.target_node_id not in visited:
                    queue.append((edge.target_node_id, depth + 1))

        return reachable

    def export_graph(self) -> Dict[str, Any]:
        """Export the entire graph as a serializable dictionary."""
        return {
            "nodes": {nid: n.model_dump(mode="json") for nid, n in self._nodes.items()},
            "edges": {eid: e.model_dump(mode="json") for eid, e in self._edges.items()},
            "current_node_id": self._current_node_id,
            "stats": {
                "total_nodes": self.node_count,
                "total_edges": self.edge_count,
                "dead_ends": len(self.get_dead_ends()),
                "stagnation_hotspots": len(self.get_stagnation_hotspots()),
            },
        }

    def compact_for_llm(self, max_nodes: int = 20) -> Dict[str, Any]:
        """Compact graph representation for LLM context."""
        recent_nodes = sorted(
            self._nodes.values(),
            key=lambda n: n.last_visited,
            reverse=True,
        )[:max_nodes]

        return {
            "total_states_explored": self.node_count,
            "current_state": self._current_node_id,
            "recent_states": [
                {
                    "id": n.node_id[:8],
                    "url": n.url_pattern,
                    "type": n.page_type,
                    "visits": n.visit_count,
                    "success_rate": round(n.success_rate, 2),
                }
                for n in recent_nodes
            ],
            "stagnation_risk": len(self.get_stagnation_hotspots()) > 0,
            "dead_ends": len(self.get_dead_ends()),
        }
