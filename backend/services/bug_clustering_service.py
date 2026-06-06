from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def cluster_bugs(bug_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for bug in bug_cards:
        root_cause = bug.get("root_cause") or bug.get("technical_explanation") or bug.get("bug_type") or "unknown"
        affected = bug.get("affected_component") or bug.get("workflow") or "unknown"
        key = f"{root_cause}:{affected}"
        clusters[key].append(bug)

    output = []
    for key, items in sorted(clusters.items(), key=lambda item: (-len(item[1]), item[0])):
        root = items[0]
        output.append({
            "cluster_key": key,
            "root_cause": root.get("root_cause") or root.get("technical_explanation") or "unknown",
            "affected_areas": sorted({item.get("workflow_stage") or item.get("workflow") or "unknown" for item in items}),
            "bug_count": len(items),
            "severity": _highest_severity(items),
            "bugs": items,
        })
    return output


def _highest_severity(items: List[Dict[str, Any]]) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    best = "low"
    for item in items:
        severity = str(item.get("severity", "low")).lower()
        if order.get(severity, 0) > order.get(best, 0):
            best = severity
    return best
