from typing import List, Dict
import random
import logging

logger = logging.getLogger(__name__)


class FormFuzzingService:
    """Heuristic form fuzzing to exercise common validation rules.

    Methods are synchronous to integrate with existing sync Playwright runner.
    """

    COMMON_INPUTS = [
        "",  # empty
        "invalid-email",
        "user@example.com",
        "a" * 300,
        "'; DROP TABLE users; --",
        "<script>alert(1)</script>",
        "P@ssw0rd",
        "weak",
        "!@#$%^&*()_+|~=`{}[]:;<>?,./",
    ]

    def __init__(self, max_tests: int = 6):
        self.max_tests = max_tests

    def fuzz_forms(self, page, folder_path: str, test_id: str) -> List[Dict[str, any]]:
        results = []
        forms = page.query_selector_all("form")
        if not forms:
            return [{"form_count": 0, "note": "no forms found"}]

        for i, form in enumerate(forms):
            if i >= 6:
                break
            inputs = form.query_selector_all("input, textarea, select")
            # run a few generated tests
            for t in range(min(self.max_tests, len(self.COMMON_INPUTS))):
                vals = {}
                for inp in inputs:
                    name = inp.get_attribute("name") or inp.get_attribute("id") or "input"
                    vals[name] = random.choice(self.COMMON_INPUTS)
                    try:
                        inp.fill(vals[name])
                    except Exception:
                        try:
                            inp.evaluate("el => el.value = arguments[0]", vals[name])
                        except Exception:
                            pass
                # attempt submit
                try:
                    form.evaluate("f => f.submit()")
                except Exception:
                    try:
                        # try to find submit button
                        btn = form.query_selector("button[type=submit], input[type=submit]")
                        if btn:
                            btn.click()
                    except Exception:
                        pass

                page.wait_for_timeout(800)
                # capture a small snapshot
                try:
                    snapshot = page.content()[:200]
                except Exception:
                    snapshot = None

                results.append({"form_index": i, "trial": t, "values": vals, "snapshot_sample": snapshot})

        return results
