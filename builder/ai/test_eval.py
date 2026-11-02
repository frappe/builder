from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, call, patch

from builder.ai.agent.tools.plugins import run_write_plugin
from builder.ai.eval import SCENARIOS, ScenarioRun


class TestEvalIsolation(TestCase):
	def run_case(self):
		scenario = next(scenario for scenario in SCENARIOS if scenario.name == "editor-plugin")
		return ScenarioRun(scenario, "m", None, "/tmp/bob-eval")

	def test_plugin_eval_validates_without_installing_or_loading(self):
		run = self.run_case()
		ctx = SimpleNamespace(page_id="scratch", plugins_written=[], require_skill=lambda name: None)
		args = {
			"name": "eval-audit",
			"label": "Eval Audit",
			"description": "Audit the page.",
			"code": "export default { install() {} };",
		}
		with (
			patch("builder.ai.agent.tools.plugins.is_plugin_manager", return_value=True),
			patch("builder.plugins.bob.get_or_new_installation") as install,
			patch("builder.ai.agent.tools.plugins.wait_for_report") as report,
			run.sandbox(),
		):
			result = run_write_plugin(ctx, args)
		self.assertIn("nothing installed or loaded", result)
		self.assertEqual(run.plugin_writes, [{"name": args["name"], "code": args["code"]}])
		install.assert_not_called()
		report.assert_not_called()

	def test_cleanup_only_deletes_exact_documents_created_by_the_run(self):
		run = self.run_case()
		run.created = [("Builder Page", "scratch"), ("Builder AI Session", "scratch-session")]
		with patch("frappe.db"), patch("frappe.delete_doc") as delete, patch("frappe.get_all") as search:
			run.clean_up()
		self.assertEqual(
			delete.call_args_list,
			[
				call(
					"Builder AI Session",
					"scratch-session",
					force=True,
					ignore_permissions=True,
					ignore_missing=True,
				),
				call("Builder Page", "scratch", force=True, ignore_permissions=True, ignore_missing=True),
			],
		)
		search.assert_not_called()

	def test_insert_tracking_ignores_existing_and_other_doctypes(self):
		from frappe.model.document import Document

		run = self.run_case()
		with (
			patch.object(Document, "db_insert", lambda doc: doc),
			patch("frappe.db.exists", side_effect=lambda doctype, name: name == "existing"),
			run.sandbox(),
		):
			Document.db_insert(SimpleNamespace(doctype="Builder Page", name="scratch"))
			Document.db_insert(SimpleNamespace(doctype="Builder Page", name="existing"))
			Document.db_insert(SimpleNamespace(doctype="Error Log", name="other"))
		self.assertEqual(run.created, [("Builder Page", "scratch")])

	def test_a_rejected_write_does_not_pass_the_plugin_scenario(self):
		run = self.run_case()
		runner = SimpleNamespace(
			trace=[{"tools": [{"name": "write_plugin", "args": {}}]}], session_id="scratch-session"
		)
		with (
			patch.object(run, "final_reply", return_value={}),
			patch("builder.ai.eval.run_measures", return_value={}),
		):
			self.assertFalse(run.score(runner, Mock())["ok"])
			run.plugin_writes.append({"name": "audit", "code": "export default {}"})
			self.assertTrue(run.score(runner, Mock())["ok"])
