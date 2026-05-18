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
