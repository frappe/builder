import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import events
from builder.ai.effects import EffectReceipt, restore_effects
from builder.ai.revisions import page_revision
from builder.ai.runs import AIRun
from builder.ai.session import AISession
from builder.ai.transactions import ToolSavepoint


class TestEffectsAndEvents(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Bob completion regression"}
		).insert()
		self.session = AISession.create({"page": self.page.name})
		self.run, _ = AIRun.admit(self.session.name, self.page.name, "fixture")
		frappe.db.set_value(AIRun.DOCTYPE, self.run.name, "status", "running")
		self.ctx = SimpleNamespace(
			page_id=self.page.name,
			run_id=self.run.name,
			current_tool_call="call-1",
			expected_revision=page_revision(self.page.name),
		)

	def receipt(self):
		return EffectReceipt(
			self.ctx, {"tool_name": "update_page_settings", "args": {"page_title": "Changed"}}
		)

	def test_replay_and_manual_edit_conflict(self):
		receipt = self.receipt()
		receipt.begin()
		self.page.page_title = "Changed"
		self.page.save()
		receipt.finish("Applied", [])
		self.assertEqual(self.receipt().replay()["result"], "Applied")
		self.page.page_title = "Independent change"
		self.page.save()
		with self.assertRaisesRegex(ValueError, "changed since"):
			restore_effects([self.run.name])
		self.assertEqual(
			frappe.db.get_value("Builder Page", self.page.name, "page_title"), "Independent change"
		)

	def test_receipt_undo_restores_page_and_shared_script_together(self):
		script = frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"script_type": "JavaScript",
				"script": "console.log('before')",
			}
		).insert()
		receipt = self.receipt()
		receipt.begin()
		try:
			self.page.page_title = "Changed"
			self.page.save()
			script.script = "console.log('after')"
			script.save()
			receipt.finish("Applied", [])
		finally:
			receipt.close()
		self.assertTrue(restore_effects([self.run.name]))
		self.assertEqual(
			frappe.db.get_value("Builder Page", self.page.name, "page_title"), "Bob completion regression"
		)
		self.assertEqual(
			frappe.db.get_value("Builder Client Script", script.name, "script"), "console.log('before')"
		)

	def test_cancelled_or_retired_run_cannot_mutate(self):
		for field, value in [("cancel_requested", 1), ("status", "interrupted")]:
			frappe.db.set_value(AIRun.DOCTYPE, self.run.name, field, value)
			with self.assertRaisesRegex(ValueError, "no longer owns"):
				self.receipt().begin()

	def test_rolled_back_event_does_not_leave_a_gap(self):
		first = events.append(self.run.name, "stream", {"chunk": "a"})
		savepoint = ToolSavepoint("event_gap")
		events.append(self.run.name, "stream", {"chunk": "discarded"})
		savepoint.rollback()
		second = events.append(self.run.name, "stream", {"chunk": "b"})
		self.assertEqual([first["seq"], second["seq"]], [1, 2])
		rows = events.replay(self.run.name)
		self.assertEqual([row["data"]["chunk"] for row in rows["events"]], ["a", "b"])

	def test_event_replay_checks_session_owner(self):
		with patch.object(AISession, "get", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				events.replay(self.run.name)

	def test_page_deletion_removes_owned_artifacts_and_run_journal(self):
		from builder.ai.artifacts import Artifact

		artifact = Artifact.save(self.page.name, "design", {"label": "Fixture"}, run=self.run.name)
		events.append(self.run.name, "stream", {"chunk": "Fixture"})
		AIRun.finish(self.run.name, "complete")
		frappe.delete_doc("Builder Page", self.page.name)
		self.assertFalse(frappe.db.exists("Builder AI Artifact", artifact.name))
		self.assertFalse(frappe.db.exists("Builder AI Event", {"run": self.run.name}))
		self.assertFalse(frappe.db.exists("Builder AI Run", self.run.name))
		self.assertFalse(frappe.db.exists("Builder AI Session", self.session.name))

	def test_page_deletion_refuses_an_active_run(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Stop the active"):
			frappe.delete_doc("Builder Page", self.page.name)
		self.assertTrue(frappe.db.exists("Builder Page", self.page.name))
		self.assertTrue(frappe.db.exists("Builder AI Run", self.run.name))

	def test_receipt_identity_cannot_be_reused_for_different_arguments(self):
		receipt = self.receipt()
		receipt.begin()
		receipt.finish("No change", [])
		op = json.loads(json.dumps(receipt.op))
		op["args"]["page_title"] = "Different"
		with self.assertRaisesRegex(ValueError, "different arguments"):
			EffectReceipt(self.ctx, op).replay()
