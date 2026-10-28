from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools import plugins
from builder.builder.tests.plugin_fixtures import drop_installations, make_installation, make_user

PLUGIN = "bob/alt-audit"
CODE = "export default { install() {} }"
ARGS = {
	"name": "alt-audit",
	"label": "Alt audit",
	"description": "Finds images with no alt text.",
	"code": CODE,
}
OK_REPORT = {"registered": [{"surface": "leftPanelTabs", "name": "alt-audit", "label": "Alt audit"}]}


def ctx(page_id="page-1"):
	return SimpleNamespace(
		page_id=page_id,
		user="Administrator",
		plugins_written=[],
		emitted=[],
		interruptible_sleep=lambda s: None,
	)


def write(context, report=None, **args):
	"""write_plugin with the editor's answer stubbed. The commit is stubbed so the test can roll back."""
	context.emit = lambda event, **kwargs: context.emitted.append((event, kwargs))
	with (
		patch.object(frappe.db, "commit"),
		patch.object(plugins.drafts, "get_load_report", return_value=report),
		patch.object(plugins, "LOAD_REPORT_TIMEOUT", 0.5),
	):
		return plugins.run_write_plugin(context, {**ARGS, **args})


class TestWritePlugin(FrappeTestCase):
	def setUp(self):
		drop_installations(PLUGIN)
		self.addCleanup(drop_installations, PLUGIN)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_the_editor_loads_the_draft_and_bob_hears_what_it_added(self):
		context = ctx()

		result = write(context, OK_REPORT)

		self.assertIn('left bar tab "Alt audit"', result)
		self.assertEqual(context.plugins_written, [PLUGIN])
		event, payload = context.emitted[0]
		op = payload["operations"][0]
		self.assertEqual(
			[event, op["tool_name"], op["args"]["plugin"]], ["tool_batch", "load_plugin", PLUGIN]
		)
		self.assertTrue(op["args"]["entry_url"].endswith("/main.js"))

	def test_each_editor_answer_reads_as_a_next_step(self):
		cases = {
			"did not report back": None,
			"turned plugins off": {"disabled": True},
			"nothing changed": {"unchanged": True},
			"did not load": {"error": "TypeError: x is undefined"},
			"needs a fix": {**OK_REPORT, "problems": ["alt-audit: the icon draws nothing."]},
			"registered nothing": {"registered": []},
		}
		for expected, report in cases.items():
			with self.subTest(expected=expected):
				self.assertIn(expected, write(ctx(), report))

	def test_the_full_plugin_id_works_as_a_name(self):
		write(ctx(page_id=None), name=PLUGIN)

		self.assertTrue(frappe.db.exists("Builder Plugin", {"plugin": PLUGIN}))

	def test_a_syntax_error_saves_nothing(self):
		with patch.object(plugins.drafts, "syntax_error", return_value="main.js:1 SyntaxError"):
			result = write(ctx(), code="export default {")

		self.assertTrue(result.startswith("FAILED"))
		self.assertFalse(frappe.db.exists("Builder Plugin", {"plugin": PLUGIN}))

	def test_a_chat_without_an_editor_saves_for_the_next_load(self):
		context = ctx(page_id=None)

		result = write(context)

		self.assertIn("next time", result)
		self.assertEqual(context.emitted, [])

	def test_a_turned_off_plugin_is_saved_but_not_loaded(self):
		make_installation(PLUGIN, source="Bob", checksum=None, enabled=0)

		result = write(ctx())

		self.assertIn("turned off", result)

	def test_only_a_plugin_manager_gets_one(self):
		frappe.set_user(make_user("plugin-blogger@example.com", roles=("Blogger",)))

		self.assertTrue(write(ctx()).startswith("DECLINED"))

	def test_read_plugin_lists_and_reads(self):
		write(ctx(page_id=None))
		make_installation("acme/listed", source="Hub")
		self.addCleanup(drop_installations, "acme/listed")

		listing = plugins.run_read_plugin(ctx(), {})
		code = plugins.run_read_plugin(ctx(), {"name": "alt-audit"})

		self.assertIn(f"{PLUGIN}: Alt audit (Bob, draft only this user runs)", listing)
		self.assertIn("acme/listed", listing)
		self.assertIn(CODE, code)
		self.assertIn("cannot change it", plugins.run_read_plugin(ctx(), {"name": "acme/listed"}))
		self.assertTrue(plugins.run_read_plugin(ctx(), {"name": "missing"}).startswith("FAILED"))

	def test_an_editor_that_cannot_be_reached_is_reported(self):
		context = ctx()

		def fail(event, **kwargs):
			raise ConnectionError("realtime is down")

		with patch.object(frappe.db, "commit"):
			context.emit = fail
			doc = plugins.drafts.save_draft("alt-audit", "Alt audit", "Finds images.", CODE)
			result = plugins.load_in_editor(context, doc)

		self.assertIn("could not be asked to load it (realtime is down)", result)

	def test_the_listing_says_who_runs_each_plugin(self):
		write(ctx(page_id=None))
		plugins.drafts.share_draft(PLUGIN)
		write(ctx(page_id=None), code=CODE + "\n// 2")
		frappe.db.set_value("Builder Plugin", {"plugin": PLUGIN}, "enabled", 0)

		self.assertIn(
			"shared, with this user's unshared draft, turned off", plugins.run_read_plugin(ctx(), {})
		)

	def test_the_chat_names_the_plugin_being_built(self):
		from builder.ai.agent.loop import activity_summary

		self.assertEqual(activity_summary("write_plugin", {"label": "Alt audit"}), "Built plugin: Alt audit")
		self.assertEqual(activity_summary("write_plugin", {}, done=False), "Building a plugin")
