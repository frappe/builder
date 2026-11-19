from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.registry import build_default_registry


def turn(model="openrouter/test-model"):
	return SimpleNamespace(loop_model=model, model=model, api_key="key")


def offered(ctx, skills=("forms-and-data",)):
	registry = build_default_registry()
	return {s["function"]["name"] for s in registry.schemas(set(skills), registry.unavailable(ctx))}


class TestToolAvailability(FrappeTestCase):
	def test_research_needs_an_openrouter_model(self):
		self.assertIn("research", offered(turn()))
		self.assertNotIn("research", offered(turn("codex/gpt-x")))

	def test_doctype_tools_need_doctype_create(self):
		with patch("frappe.has_permission", return_value=False):
			tools = offered(turn())

		self.assertNotIn("create_doctype", tools)
		self.assertNotIn("connect_form", tools)
		self.assertIn("write_page_data_script", tools)

	def test_a_call_to_an_unavailable_tool_is_refused(self):
		runner = AgentRunner("hi", model="m", api_key="k")
		runner.unavailable_tools = frozenset({"research"})

		out = runner.run_op({"tool_name": "research", "args": {"question": "q"}}, {})

		self.assertTrue(out.startswith("FAILED: research isn't available"), out)
