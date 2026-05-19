import logging
from typing import Any, Dict, List
import os

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class VisualIssueService:
    """Analyze screenshots for common visual issues.

    The executor should provide a list of screenshot file paths.
    This service uses heuristic checks (blank screen, excessive whitespace,
    obvious cut-off by checking aspect ratios and sampling) to flag problems.
    """

    async def analyze_visuals(self, screenshots: List[str]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        for path in screenshots:
            if not os.path.exists(path):
                issues.append({"path": path, "issue": "missing_file"})
                continue
            if PIL_AVAILABLE:
                try:
                    with Image.open(path) as im:
                        w, h = im.size
                        stat = ImageStat.Stat(im.convert("L"))
                        mean = stat.mean[0]
                        # very dark or very light screens are suspicious
                        if mean < 6 or mean > 245:
                            issues.append({"path": path, "issue": "blank_or_near_blank", "mean_brightness": mean})
                        # detect extreme aspect ratio (possible cut-off)
                        if w / h > 3 or h / w > 3:
                            issues.append({"path": path, "issue": "extreme_aspect_ratio", "size": (w, h)})
                        if size < 16000:
                            issues.append({"path": path, "issue": "low_detail_or_blank_layout", "severity": "medium"})
                except Exception as e:
                    logger.exception("Failed to analyze image %s: %s", path, e)
                    issues.append({"path": path, "issue": "read_error", "error": str(e)})
            else:
                # PIL not available — do a lightweight file-size heuristic
                try:
                    size = os.path.getsize(path)
                    if size < 2000:
                        issues.append({"path": path, "issue": "small_file_size", "size": size})
                except Exception as e:
                    issues.append({"path": path, "issue": "stat_error", "error": str(e)})

        return {"issues": issues}

    def analyze_observation(self, observation: Any) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        viewport = getattr(observation, "viewport", {}) or {}
        width = int(viewport.get("width", 0) or 0)
        height = int(viewport.get("height", 0) or 0)

        for element in getattr(observation, "elements", []) or []:
            bbox = getattr(element, "bbox", None)
            if not bbox:
                continue
            if width and height and (bbox.x < -8 or bbox.y < -8 or bbox.x + bbox.width > width + 16 or bbox.y + bbox.height > height + 16):
                issues.append(self._issue("layout_overflow", "medium", element.label or element.tag, f"Element {element.label or element.tag} extends beyond the viewport", observation))
            if not element.visible and element.enabled:
                issues.append(self._issue("invisible_click_target", "high", element.label or element.tag, f"Interactive element {element.label or element.tag} is not visible", observation))
            if element.visible and bbox.width > 0 and bbox.height > 0 and (bbox.width < 40 or bbox.height < 18):
                issues.append(self._issue("clipped_element", "medium", element.label or element.tag, f"Interactive element {element.label or element.tag} appears clipped or undersized", observation))

        for table in getattr(observation, "visible_tables", []) or []:
            rows = int(table.get("rows", 0) or 0)
            if rows == 0:
                issues.append(self._issue("empty_table", "low", table.get("caption") or "table", "Visible table has no rows", observation))

        for card in getattr(observation, "visible_cards", []) or []:
            text = str(card.get("text", "")).strip()
            bbox = card.get("bbox") or {}
            if bbox and (bbox.get("width", 0) < 60 or bbox.get("height", 0) < 20):
                issues.append(self._issue("clipped_card", "medium", text[:40] or "card", "Card appears clipped or undersized", observation))
            if text and len(text) < 3:
                issues.append(self._issue("hidden_text", "low", text[:40] or "card", "Card has little or no readable text", observation))

        for widget in getattr(observation, "dashboard_widgets", []) or []:
            text = str(widget.get("text", "")).strip()
            bbox = widget.get("bbox") or {}
            if bbox and (bbox.get("width", 0) < 60 or bbox.get("height", 0) < 20):
                issues.append(self._issue("clipped_widget", "medium", text[:40] or "widget", "Dashboard widget appears clipped or undersized", observation))

        if getattr(observation, "loading_indicators", []) and not getattr(observation, "page_text", ""):
            issues.append(self._issue("stale_loading_state", "high", getattr(observation, "page_type", "page"), "Loading indicators remain while the page is empty", observation))

        return {"issues": issues}

    @staticmethod
    def _issue(issue_type: str, severity: str, location: str, description: str, observation: Any) -> Dict[str, Any]:
        screenshot = None
        artifact = getattr(observation, "screenshot", None)
        if isinstance(artifact, dict):
            screenshot = artifact.get("path")
        else:
            screenshot = getattr(artifact, "path", None)
        return {
            "type": issue_type,
            "severity": severity,
            "location": location,
            "description": description,
            "screenshot": screenshot,
        }
