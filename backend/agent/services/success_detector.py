import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SuccessDetector:
    """Detects whether actions produced the expected success states.

    This component expects the executor to attach clear artifacts:
      - dom_snapshots: list of DOM/HTML strings captured after actions
      - console_logs: list
      - cookies: dict
      - network_logs: list
      - screenshots: list
      - expectations: list of expected assertions the workflow wanted (optional)
    """

    async def detect_all(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {"all_ok": True, "checks": []}

        expectations: List[Dict[str, Any]] = artifacts.get("expectations", []) or []

        # If no explicit expectations provided, derive basic heuristics
        if not expectations:
            expectations = self._derive_expectations(artifacts)

        for exp in expectations:
            ok, evidence = await self._check_expectation(exp, artifacts)
            results["checks"].append({"expectation": exp, "ok": ok, "evidence": evidence})
            if not ok:
                results["all_ok"] = False

        return results

    def _derive_expectations(self, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Basic fallbacks: if login flow detected, expect cookie and dashboard
        expectations: List[Dict[str, Any]] = []
        meta = artifacts.get("metadata", {}) or {}
        if meta.get("intent") == "login":
            expectations.append({"type": "cookie_exists", "name": "session"})
            expectations.append({"type": "dom_contains", "selector": ".dashboard"})
        # generic: expect non-empty DOM and at least one screenshot
        expectations.append({"type": "non_empty_dom"})
        expectations.append({"type": "screenshot_present"})
        return expectations

    async def _check_expectation(self, exp: Dict[str, Any], artifacts: Dict[str, Any]):
        t = exp.get("type")
        if t == "cookie_exists":
            name = exp.get("name")
            cookies = artifacts.get("cookies") or {}
            ok = name in cookies
            return ok, {"cookies": list(cookies.keys())}
        if t == "dom_contains":
            selector = exp.get("selector")
            doms = artifacts.get("dom_snapshots") or []
            for dom in doms:
                if selector in dom:
                    return True, {"matched_dom_sample": dom[:240]}
            return False, {"checked_selector": selector}
        if t == "non_empty_dom":
            doms = artifacts.get("dom_snapshots") or []
            ok = any(bool(d and d.strip()) for d in doms)
            return ok, {"dom_count": len(doms)}
        if t == "screenshot_present":
            ss = artifacts.get("screenshots") or []
            return (len(ss) > 0), {"screenshots": ss[:5]}

        # Unknown expectation: return not-ok with details
        logger.debug("Unknown expectation type: %s", t)
        return False, {"reason": "unknown expectation type"}
