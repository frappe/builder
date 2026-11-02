import json
import os
from unittest.mock import patch

import frappe
from frappe.handler import execute_cmd
from frappe.tests.utils import FrappeTestCase

from builder.ai import api, locks, page_writer
from builder.ai.agent.artifact import found_photo_list
from builder.ai.agent.loop import AgentRunner, run_agent_job
from builder.ai.agent.registry import Tool
from builder.ai.brief import DesignBrief, validate_asset_usage
from builder.ai.data_script import SCRIPT_PREFIX
from builder.ai.runs import AIRun
from builder.ai.session import AISession
from builder.utils import execute_script


class TestIntegrationBoundaries(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Bob integration fixture"}
		).insert()
		self.session = AISession.create({"page": self.page.name})

	def test_mutation_dispatch_rejects_get_before_effects(self):
		for method in ("run", "cancel", "confirm_pending_settings", "revert_to_message", "delete_ai_session"):
			with (
				self.subTest(method=method),
				patch.object(frappe.local, "request", frappe._dict(method="GET"), create=True),
				patch.object(frappe, "call") as invoke,
			):
				with self.assertRaises(frappe.PermissionError):
					execute_cmd(f"builder.ai.api.{method}")
				invoke.assert_not_called()

	def test_failed_tool_cleans_new_files_callbacks_and_replay(self):
		runner = AgentRunner("edit", "test/model", "test", page_id=self.page.name)
		paths, effects = [], []
		frappe.db.after_commit.add(lambda: effects.append("earlier"))

		def fail(ctx, args):
			script = frappe.get_doc(
				{
					"doctype": "Builder Client Script",
					"script_type": "JavaScript",
					"script": "console.log('test')",
				}
			).insert()
			paths.append(frappe.get_site_path("public", script.public_url.split("?")[0].lstrip("/")))
			ctx.queue_client_op({"tool_name": "set_page_blocks", "args": {"blocks": {}}})
			frappe.db.after_commit.add(lambda: effects.append("failed"))
			raise ValueError("test tool failed")

		tool = Tool(name="test_tool", side="server", handler=fail, description="test", parameters={})
		result = runner.run_handler(tool, {"tool_name": "test_tool", "args": {}})
		self.assertTrue(result.startswith("FAILED"))
		self.assertTrue(paths)
		self.assertFalse(os.path.exists(paths[0]))
		self.assertEqual(runner.pending_client_ops, [])
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
		self.assertEqual(effects, ["earlier"])

	def test_malformed_generation_never_writes_partial_draft(self):
		with patch.object(page_writer.frappe.db, "set_value") as save:
			with self.assertRaisesRegex(ValueError, "malformed"):
				page_writer.persist_page(self.page.name, "el: div\nc:\n  - el: p\n    text: 'unfinished")
			save.assert_not_called()

	def test_committed_plugin_failure_remains_an_actionable_result(self):
		runner = AgentRunner("edit", "test/model", "test", page_id=self.page.name)

		def committed_failure(ctx, args):
			frappe.db.set_value("Builder Page", self.page.name, "page_title", "Committed plugin fixture")
			frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
			return "FAILED: installed, but it did not load in the editor."

		tool = Tool(
			name="write_plugin", side="server", handler=committed_failure, description="test", parameters={}
		)
		result = runner.run_handler(tool, {"tool_name": "write_plugin", "args": {}})
		self.assertIn("installed, but", result)
		self.assertEqual(
			frappe.db.get_value("Builder Page", self.page.name, "page_title"), "Committed plugin fixture"
		)

	def test_failed_tool_restores_an_existing_realtime_buffer(self):
		from builder.ai.transactions import ToolSavepoint

		frappe.publish_realtime("bob_test_prior", {}, user="Administrator", after_commit=True)
		before = list(frappe.local._realtime_log)
		savepoint = ToolSavepoint("test_events")
		frappe.publish_realtime("bob_test_failed", {}, user="Administrator", after_commit=True)
		savepoint.rollback()
		self.assertEqual(frappe.local._realtime_log, before)
		with patch("frappe.realtime.emit_via_redis") as emit:
			frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
		self.assertIn("bob_test_prior", [call.args[0] for call in emit.call_args_list])
		self.assertNotIn("bob_test_failed", [call.args[0] for call in emit.call_args_list])

	def test_failed_first_event_does_not_disable_later_events(self):
		from builder.ai.transactions import ToolSavepoint

		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
		savepoint = ToolSavepoint("test_first_event")
		frappe.publish_realtime("bob_test_failed", {}, user="Administrator", after_commit=True)
		savepoint.rollback()
		frappe.publish_realtime("bob_test_later", {}, user="Administrator", after_commit=True)
		with patch("frappe.realtime.emit_via_redis") as emit:
			frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
		self.assertEqual([call.args[0] for call in emit.call_args_list], ["bob_test_later"])

	def test_paid_previews_and_selection_survive_new_search(self):
		brief = DesignBrief(self.page.name)
		preview = {
			"id": "magnific:1",
			"url": "",
			"thumb": "https://example.test/preview",
			"preview_only": True,
		}
		brief.remember_assets([preview])
		brief.select_assets("I want this [asset: magnific:1]")
		brief.remember_assets([{"id": str(i), "url": f"https://example.test/{i}"} for i in range(20)])
		assets = brief.read()["assets"]
		self.assertEqual(len(assets), 12)
		self.assertTrue(assets[0]["selected"])
		self.assertEqual(assets[0]["id"], "magnific:1")
		runner = AgentRunner("edit", "test/model", "test")
		runner.found_images = assets
		self.assertNotIn("preview", found_photo_list(runner))
		with self.assertRaisesRegex(ValueError, "not ready"):
			validate_asset_usage(assets, {"attrs": {"src": preview["thumb"]}})
		validate_asset_usage(assets, {"attrs": {"src": "/files/licensed-original.webp"}})

	def test_readonly_data_script_rejects_aliased_mutation(self):
		for enabled in (True, False):
			with (
				self.subTest(server_scripts_enabled=enabled),
				patch("builder.utils.is_safe_exec_enabled", return_value=enabled),
			):
				local_values = {"data": frappe._dict()}
				execute_script(SCRIPT_PREFIX + "data.title = 'safe'", local_values, "test")
				self.assertEqual(local_values["data"].title, "safe")
				with self.assertRaises(Exception):
					execute_script(
						SCRIPT_PREFIX
						+ "db = frappe.db\nwriter = db.set_value\nwriter('User', 'Administrator', 'enabled', 0)",
						local_values,
						"test",
					)
				self.assertEqual(frappe.db.get_value("User", "Administrator", "enabled"), 1)

	def test_public_reference_is_not_offered_as_page_imagery(self):
		runner = AgentRunner("edit", "test/model", "test")
		runner.found_images = [
			{"url": "/files/reference.png", "role": "reference"},
			{"url": "/files/undecided.png", "role": "undecided"},
			{"url": "/files/product.png", "role": "product"},
		]
		inventory = found_photo_list(runner)
		self.assertIn("/files/product.png", inventory)
		self.assertNotIn("/files/reference.png", inventory)
		self.assertNotIn("/files/undecided.png", inventory)

	def test_startup_failure_is_visible_in_chat(self):
		run, _ = AIRun.admit(self.session.name, self.page.name, "test/model")
		with patch("builder.ai.llm.resolve_api_key", side_effect=ValueError("no key")):
			with self.assertRaises(ValueError):
				run_agent_job("hello", "test/model", run_id=run.name)
		message = self.session.get_messages()[-1]
		self.assertIn("could not start", message["content"])
		self.assertEqual(message["metadata"]["runId"], run.name)

	def test_late_client_metadata_targets_original_run(self):
		first = self.session.append_message("assistant", "one", metadata={"runId": "first"})
		second = self.session.append_message("assistant", "two", metadata={"runId": "second"})
		api.update_session_message_metadata(self.session.name, {"affectedBlocks": ["hero"]}, run_id="first")

		def meta(name):
			return json.loads(frappe.db.get_value(AISession.MESSAGE_DOCTYPE, name, "metadata_json"))

		self.assertEqual(meta(first)["affectedBlocks"], ["hero"])
		self.assertNotIn("affectedBlocks", meta(second))

	def test_crash_recovery_preserves_snapshot_metadata(self):
		run, _ = AIRun.admit(self.session.name, self.page.name, "test/model")
		frappe.db.set_value(
			AIRun.DOCTYPE,
			run.name,
			{
				"status": "running",
				"heartbeat_on": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-20),
				"metadata_json": json.dumps({"revertSnapshot": "checkpoint", "operations": 2}),
			},
		)
		self.assertIsNone(AIRun.active(self.session.name))
		self.assertEqual(self.session.get_messages()[-1]["metadata"]["revertSnapshot"], "checkpoint")

	def test_revert_commits_before_releasing_page_lock(self):
		from builder.ai.snapshots import capture_page_state, save_revert_snapshot

		snapshot = save_revert_snapshot(self.page.name, capture_page_state(self.page.name))
		self.session.append_message("user", "edit")
		message = self.session.append_message("assistant", "done", metadata={"revertSnapshot": snapshot})
		states = []
		frappe.db.after_commit.add(lambda: states.append(locks.held(locks.page_key(self.page.name))))
		api.revert_to_message(self.session.name, message)
		self.assertEqual(states, [True])
		self.assertFalse(locks.held(locks.page_key(self.page.name)))
