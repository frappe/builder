import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.brief import DesignBrief
from builder.ai.runs import AIRun, dispatch_run
from builder.ai.session import AISession


class TestRunLifecycle(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Run lifecycle fixture"}
		).insert()
		self.session = AISession.create({"page": self.page.name})

	def admit(self, request_id=None):
		return AIRun.admit(self.session.name, self.page.name, "test/model", request_id)

	def test_queued_run_blocks_another_turn(self):
		first, created = self.admit()
		second, second_created = self.admit()
		self.assertTrue(created)
		self.assertIsNone(second)
		self.assertFalse(second_created)
		self.assertEqual(AIRun.active(self.session.name).name, first.name)

	def test_request_retry_returns_original_run(self):
		request_id = frappe.generate_hash(length=24)
		first, _ = self.admit(request_id)
		second, created = self.admit(request_id)
		self.assertFalse(created)
		self.assertEqual(first.name, second.name)

	def test_stop_before_worker_claim_prevents_execution(self):
		run, _ = self.admit()
		self.assertEqual(AIRun.cancel(run.name), "cancelled")
		self.assertFalse(AIRun.claim(run.name))
		self.assertIsNone(AIRun.active(self.session.name))
		self.assertEqual(frappe.db.get_value(AIRun.DOCTYPE, run.name, "cancel_requested"), 1)

	def test_stale_stop_does_not_cancel_new_run(self):
		old, _ = self.admit()
		AIRun.finish(old.name, "complete")
		current, _ = self.admit()
		self.assertEqual(api.cancel(self.session.name, old.name)["status"], "not_running")
		self.assertEqual(AIRun.active(self.session.name).name, current.name)

	def test_hydration_recovers_queued_run(self):
		run, _ = self.admit()
		result = api.get_ai_session(self.page.name, session_id=self.session.name)
		self.assertEqual(result["active_run"]["run_id"], run.name)
		self.assertEqual(result["active_run"]["status"], "queued")

	def test_lost_first_acceptance_resolves_request(self):
		request = frappe.generate_hash(length=24)
		run, _ = self.admit(request)
		result = api.get_ai_session(self.page.name, request_id=request)
		self.assertEqual(result["session_id"], self.session.name)
		self.assertEqual(result["request_run"]["run_id"], run.name)

	def test_dispatch_failure_leaves_retryable_payload(self):
		run, _ = self.admit()
		payload = {"prompt": "hello", "model": "test/model", "run_id": run.name}
		frappe.db.set_value(AIRun.DOCTYPE, run.name, "payload_json", json.dumps(payload))
		with (
			patch.dict(frappe.conf, {"builder_ai_runtime": "rq"}),
			patch("frappe.enqueue", side_effect=ConnectionError),
		):
			dispatch_run(run.name)
		self.assertEqual(frappe.db.get_value(AIRun.DOCTYPE, run.name, "status"), "queued")
		with patch.dict(frappe.conf, {"builder_ai_runtime": "rq"}), patch("frappe.enqueue") as enqueue:
			dispatch_run(run.name)
		self.assertTrue(enqueue.call_args.kwargs["deduplicate"])
		self.assertEqual(enqueue.call_args.kwargs["run_id"], run.name)

	def test_async_dispatch_keeps_payload_for_daemon_without_rq_job(self):
		run, _ = self.admit()
		frappe.db.set_value(AIRun.DOCTYPE, run.name, "payload_json", '{"prompt":"fixture"}')
		with patch.dict(frappe.conf, {"builder_ai_runtime": "async"}), patch("frappe.enqueue") as enqueue:
			dispatch_run(run.name)
			enqueue.assert_not_called()
		self.assertEqual(frappe.db.get_value(AIRun.DOCTYPE, run.name, "status"), "queued")

	def test_expired_snapshot_keeps_history_and_page(self):
		self.session.append_message("user", "Change the heading")
		message = self.session.append_message("assistant", "Changed", metadata={"revertSnapshot": "missing"})
		before = self.session.get_messages()
		with self.assertRaises(frappe.ValidationError):
			api.revert_to_message(self.session.name, message)
		self.assertEqual(self.session.get_messages(), before)

	def test_revert_restores_page_and_conversation_together(self):
		from builder.ai.snapshots import capture_page_state, save_revert_snapshot

		original = json.dumps([{"blockId": "root", "element": "div", "children": []}])
		frappe.db.set_value("Builder Page", self.page.name, "draft_blocks", original)
		snapshot = save_revert_snapshot(self.page.name, capture_page_state(self.page.name))
		self.session.append_message("user", "Change the page")
		message = self.session.append_message("assistant", "Changed", metadata={"revertSnapshot": snapshot})
		frappe.db.set_value(
			"Builder Page", self.page.name, "draft_blocks", '[{"blockId":"other","element":"div"}]'
		)
		result = api.revert_to_message(self.session.name, message)
		self.assertEqual(result["messages"], [])
		self.assertEqual(
			json.loads(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks")),
			json.loads(original),
		)

	def test_revert_does_not_erase_confirmed_external_action_history(self):
		from builder.ai.snapshots import capture_page_state, save_revert_snapshot

		snapshot = save_revert_snapshot(self.page.name, capture_page_state(self.page.name))
		message = self.session.append_message(
			"assistant", "Before purchase", metadata={"revertSnapshot": snapshot}
		)
		self.session.append_message(
			"assistant",
			"Acquired original",
			metadata={"status": "action_applied", "kind": "acquire_paid_asset"},
		)
		before = self.session.get_messages()
		with self.assertRaisesRegex(ValueError, "confirmed external"):
			frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
			api.revert_to_message(self.session.name, message)
		self.assertEqual(self.session.get_messages(), before)

	def test_failed_restore_keeps_the_conversation(self):
		from builder.ai.snapshots import capture_page_state, save_revert_snapshot

		frappe.db.set_value(
			"Builder Page", self.page.name, "draft_blocks", '[{"blockId":"root","element":"div"}]'
		)
		snapshot = save_revert_snapshot(self.page.name, capture_page_state(self.page.name))
		self.session.append_message("user", "Edit")
		message = self.session.append_message("assistant", "Changed", metadata={"revertSnapshot": snapshot})
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- Exercise real commit/rollback behavior in this regression.
		with patch(
			"builder.builder.doctype.builder_page.builder_page.BuilderPage.restore_snapshot",
			side_effect=frappe.ValidationError,
		):
			with self.assertRaises(frappe.ValidationError):
				api.revert_to_message(self.session.name, message)
		self.assertEqual(len(self.session.get_messages()), 2)

	def test_page_brief_survives_new_chat_and_preserves_other_fields(self):
		brief = DesignBrief(self.page.name)
		brief.update({"project": "Field Notes", "audience": "Local artists", "stage": "discover"})
		AISession.create({"page": self.page.name})
		updated = brief.update({"stage": "directions", "visual_direction": "An illustrated field guide"})
		self.assertEqual(updated["project"], "Field Notes")
		self.assertEqual(updated["revision"], 2)
		with self.assertRaises(ValueError):
			brief.update({"stage": "invented"})
		self.assertEqual(brief.read()["revision"], 2)

	def test_invalid_model_persists_no_prompt(self):
		with (
			patch.object(api.ModelRegistry, "get_default", return_value="missing"),
			patch.object(api.ModelRegistry, "is_known_model", return_value=False),
		):
			with self.assertRaises(frappe.ValidationError):
				api.run("hello", self.page.name, session_id=self.session.name)
		self.assertEqual(self.session.get_messages(), [])

	def test_delete_active_session_is_rejected(self):
		self.admit()
		with self.assertRaises(frappe.ValidationError):
			api.delete_ai_session(self.session.name)
		self.assertTrue(frappe.db.exists(AISession.DOCTYPE, self.session.name))
