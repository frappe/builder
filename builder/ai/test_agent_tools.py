"""The tools a hosting app lets Bob have (builder_agent_tools): frappe.page gives its own site's
editor page tools only, and a call to any other tool must be refused, not run."""

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.registry import build_default_registry
from builder.ai.agent.tools.skills import run_read_skill
from builder.ai.stock_look import FontDraw
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

	def test_the_model_hears_which_tools_the_host_withheld(self):
		"""His instructions name search_images and set_page_script, and his next steps become buttons"""
		with hosting_hooks(builder_agent_tools=[page_tools]):
			runner = AgentRunner("hi", model="m", api_key="k", page_id="page-x")

		context = runner.build_withheld_context()

		for name in ("search_images", "set_page_script", "connect_form", "run_python"):
			self.assertIn(name, context)
		self.assertNotIn("read_page", context)
		self.assertIn("as a next step", context)

	def test_nothing_is_said_where_no_hook_limits_the_tools(self):
		with hosting_hooks(builder_agent_tools=[no_say]):
			runner = AgentRunner("hi", model="m", api_key="k", page_id="page-x")

		self.assertEqual(runner.build_withheld_context(), "")

	def test_a_run_kept_off_the_web_is_offered_no_font_draw(self):
		"""The draw's faces load from Google Fonts, and frappe.page's own site loads no font from outside"""

		def runner(hook):
			with hosting_hooks(builder_agent_tools=[hook]):
				return AgentRunner("hi", model="m", api_key="k", page_id="page-x", session_id="chat-a")

		draw = ", ".join(FontDraw("chat-a").sample())
		self.assertIn(draw, runner(no_say).attach_skill("new-page", "For this page"))
		self.assertIn(draw, run_read_skill(runner(no_say), {"name": "new-page"}))

		for guide in (
			runner(page_tools).attach_skill("new-page", "For this page"),
			run_read_skill(runner(page_tools), {"name": "new-page"}),
		):
			self.assertNotIn(draw, guide)
			self.assertNotIn("Google Fonts catalogue", guide)
			self.assertNotIn("{{", guide)
			self.assertIn("in any of their cuts: Fraunces", guide)
