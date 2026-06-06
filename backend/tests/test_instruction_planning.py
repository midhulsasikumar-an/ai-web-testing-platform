import unittest

from backend.services.instruction_parser import parse_instruction_context
from backend.services.scenario_expansion_service import expand_scenarios


class InstructionPlanningTests(unittest.TestCase):
    def test_parser_extracts_inline_credentials_and_strips_them_from_scenarios(self):
        instruction = (
            "Run login with username: demo_user and password: demo_pass\n"
            "Then verify navigation and APIs\n"
            "Also include recovery scenarios"
        )

        context = parse_instruction_context(instruction)
        self.assertEqual(context["credentials"], {"username": "demo_user", "password": "demo_pass"})
        self.assertNotIn("demo_user", context["sanitized_instruction"])
        self.assertNotIn("demo_pass", context["sanitized_instruction"])

        plan = expand_scenarios(
            "https://example.com",
            context["sanitized_instruction"],
            dom={"inputs": [{"type": "password"}], "buttons": [], "links": []},
            discovery={
                "feature_map": [{"feature_key": "AUTHENTICATION", "feature_name": "Login"}],
                "workflows": [],
                "forms": [],
                "pages": [],
                "discovered_pages": [],
            }
        )

        self.assertTrue(plan["scenario_cases"])
