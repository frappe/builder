"""The tools a hosting app lets Bob have (builder_agent_tools): frappe.page gives its own site's
editor page tools only, and a call to any other tool must be refused, not run."""

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.registry import build_default_registry
from builder.builder.tests.hosting_hooks import hosting_hooks, no_say, page_tools, preview_tools


def offered(**hooks) -> set[str]:
	with hosting_hooks(**hooks):
		return set(build_default_registry().names())


class TestAgentToolsHook(FrappeTestCase):
	def test_every_tool_is_offered_without_a_hook_that_limits_them(self):
		every_tool = offered(builder_agent_tools=[])

		self.assertLessEqual({"run_python", "query_records", "set_home_page", "write_plugin"}, every_tool)
		self.assertEqual(offered(builder_agent_tools=[no_say]), every_tool)

	def test_only_the_tools_the_hooks_allow_are_offered(self):
		self.assertEqual(offered(builder_agent_tools=[page_tools]), {"read_page", "edit_page"})
		self.assertEqual(
			offered(builder_agent_tools=[no_say, page_tools, preview_tools]),
			{"read_page", "edit_page", "preview_page"},
		)

	def test_the_model_is_sent_only_the_allowed_tools(self):
		with hosting_hooks(builder_agent_tools=[page_tools]):
			registry = build_default_registry()

		self.assertEqual(
			{schema["function"]["name"] for schema in registry.schemas()}, {"read_page", "edit_page"}
		)

	def test_a_call_to_a_withheld_tool_is_refused(self):
		"""A name the registry does not know runs as a client op, and set_page_script is one"""
		with hosting_hooks(builder_agent_tools=[page_tools]):
			runner = AgentRunner("hi", model="m", api_key="k", page_id="page-x")

		for name in ("run_python", "set_page_script", "set_home_page"):
			op = {"tool_name": name, "args": {}}
			self.assertEqual(runner.op_kind(op), "withheld")
			self.assertTrue(runner.run_op(op, {}).startswith("FAILED"))
		self.assertEqual(runner.op_kind({"tool_name": "read_page", "args": {}}), "server")
