import json
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent import pending


class TestRequestConfirmation(FrappeTestCase):
	def test_persists_the_turns_steps_and_trace_on_the_card(self):
		session = frappe.get_doc({"doctype": "Builder AI Session", "session_user": "Administrator"}).insert()
		ctx = SimpleNamespace(
			session_id=session.name,
			timeline=lambda: [{"id": 0, "kind": "tool", "tool": "generate_page", "status": "done"}],
			trace=[{"round": 0, "tools": [{"name": "generate_page", "args": "{}"}], "text": ""}],
			loop_model="openrouter/test-model",
			emit=lambda *args, **kwargs: None,
		)

		pending.request_confirmation(ctx, "create_doctype", "Create it?", {"name": "X", "fields": [1]})

		message = frappe.get_all(
			"Builder AI Message", filters={"session": session.name}, fields=["status", "metadata_json"]
		)[0]
		meta = json.loads(message.metadata_json)
		self.assertEqual(message.status, "pending_action")
		self.assertEqual(meta["steps"][0]["tool"], "generate_page")
		self.assertEqual(meta["debug"]["trace"][0]["tools"][0]["name"], "generate_page")
