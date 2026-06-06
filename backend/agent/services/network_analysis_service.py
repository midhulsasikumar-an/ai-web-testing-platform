from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class NetworkAnalysisService:
    """Analyze network logs collected during execution.

    Expected input: a list of network request entries with fields:
      - url, status, method, resource_type, duration_ms, error
    """

    async def analyze_network(self, network_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        counts = {"total": len(network_logs), "errors": 0, "timeouts": 0, "server_errors": 0}

        for entry in network_logs:
            status = entry.get("status")
            err = entry.get("error")
            if err:
                counts["errors"] += 1
                failures.append(entry)
            if status is not None:
                if isinstance(status, int) and 500 <= status < 600:
                    counts["server_errors"] += 1
                    issues.append({"type": "5xx", "entry": entry})
                if status == 0 or status is False:
                    counts["timeouts"] += 1
                    issues.append({"type": "timeout", "entry": entry})

        summary = {
            "summary": counts,
            "errors": failures,
            "issues": issues,
        }
        logger.debug("Network analysis summary: %s", counts)
        return summary
