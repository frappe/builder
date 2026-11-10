from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner


def get_app_context(page_id):
	return f"Instructions for {page_id}"


def get_no_context(page_id):
	return None


def hooks(hook, *args, **kwargs):
	if hook == "builder_agent_context":
		return [f"{__name__}.get_app_context", f"{__name__}.get_no_context"]
	return []


class TestAgentContext(FrappeTestCase):
	def test_apps_add_instructions_for_the_open_page(self):
		runner = AgentRunner("hi", model="m", api_key="k", page_id="page-x")
		with patch("frappe.get_hooks", side_effect=hooks):
			self.assertEqual(runner.build_agent_context(), "Instructions for page-x")

	def test_no_open_page_means_no_app_instructions(self):
		runner = AgentRunner("hi", model="m", api_key="k")
		with patch("frappe.get_hooks", side_effect=hooks):
			self.assertEqual(runner.build_agent_context(), "")
