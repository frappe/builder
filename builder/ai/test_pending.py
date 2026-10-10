import json
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent import pending
from builder.ai.api import confirm_pending_settings
from builder.ai.session import AISession

SEED_DOCTYPE = "Bob Seed Test Item"


def user_with_role(role: str) -> str:
	email = f"bob-pending-{frappe.scrub(role).replace('_', '-')}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Bob Test", "roles": [{"role": role}]}
		).insert(ignore_permissions=True)
	return email


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


class TestApplyPendingAction(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_website_manager_cannot_seed_users(self):
		frappe.set_user(user_with_role("Website Manager"))
		row = {
			"email": "bob-seeded@example.com",
			"first_name": "Seeded",
			"roles": [{"role": "System Manager"}],
		}

		with self.assertRaises(frappe.PermissionError):
			pending.apply_pending_action("seed_sample_data", {"doctype": "User", "rows": [row]})
		self.assertFalse(frappe.db.exists("User", "bob-seeded@example.com"))

	def test_a_website_manager_cannot_create_a_doctype(self):
		frappe.set_user(user_with_role("Website Manager"))

		with self.assertRaises(frappe.PermissionError):
			pending.apply_pending_action(
				"create_doctype", {"name": "Bob Forbidden Type", "fields": [{"fieldname": "title"}]}
			)
		self.assertFalse(frappe.db.exists("DocType", "Bob Forbidden Type"))

	def test_a_website_manager_cannot_connect_a_form(self):
		frappe.set_user(user_with_role("Website Manager"))
		payload = {
			"doctype_name": "Bob Forbidden Submission",
			"fields": [{"fieldname": "email", "label": "Email", "fieldtype": "Data"}],
			"form_selector": "form",
		}

		with self.assertRaises(frappe.PermissionError):
			pending.apply_pending_action("connect_form", payload)
		self.assertFalse(frappe.db.exists("DocType", "Bob Forbidden Submission"))

	def test_a_system_manager_can_create_and_seed_a_doctype(self):
		doctype = f"{SEED_DOCTYPE} {frappe.generate_hash(length=6)}"
		frappe.set_user(user_with_role("System Manager"))
		try:
			pending.apply_pending_action(
				"create_doctype", {"name": doctype, "fields": [{"fieldname": "title"}]}
			)
			pending.apply_pending_action(
				"seed_sample_data", {"doctype": doctype, "rows": [{"title": "Seeded"}]}
			)

			self.assertTrue(frappe.db.exists(doctype, {"title": "Seeded"}))
			self.assertFalse(frappe.get_all("DocPerm", {"parent": doctype, "role": "Guest"}))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True)

	def test_a_system_manager_can_connect_a_form(self):
		frappe.set_user(user_with_role("System Manager"))
		payload = {
			"doctype_name": "Bob Connect Test Submission",
			"fields": [{"fieldname": "email", "label": "Email", "fieldtype": "Data"}],
			"form_selector": "form",
		}

		pending.apply_pending_action("connect_form", payload)

		self.assertTrue(frappe.db.exists("Web Form", {"doc_type": "Bob Connect Test Submission"}))

	def test_connect_form_will_not_wire_an_existing_doctype(self):
		frappe.set_user(user_with_role("System Manager"))
		payload = {
			"doctype_name": "User",
			"fields": [{"fieldname": "email", "label": "Email", "fieldtype": "Data"}],
			"form_selector": "form",
		}

		with self.assertRaises(frappe.ValidationError):
			pending.apply_pending_action("connect_form", payload)
		self.assertFalse(frappe.db.exists("Web Form", {"doc_type": "User", "login_required": 0}))

	def test_a_website_manager_cannot_write_chat_messages_directly(self):
		user = user_with_role("Website Manager")
		session = frappe.get_doc({"doctype": "Builder AI Session", "session_user": user}).insert()
		frappe.set_user(user)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Builder AI Message",
					"session": session.name,
					"role": "assistant",
					"content": "Apply?",
					"status": "pending_action",
				}
			).insert()


class TestConfirmPendingSettings(FrappeTestCase):
	def pending_message(self) -> str:
		session = frappe.get_doc({"doctype": "Builder AI Session", "session_user": "Administrator"}).insert()
		metadata = {"status": "pending_action", "kind": "home_page", "payload": {"route": "bob-home"}}
		return AISession.try_append_message(session.name, "assistant", "Apply?", metadata=metadata)

	def test_a_pending_action_is_claimed_once(self):
		message_id = self.pending_message()

		self.assertTrue(AISession.claim_pending_action(message_id, "action_applied"))
		self.assertFalse(AISession.claim_pending_action(message_id, "action_skipped"))
		self.assertEqual(frappe.db.get_value("Builder AI Message", message_id, "status"), "action_applied")

	def test_a_second_confirm_does_not_apply_again(self):
		message_id = self.pending_message()
		confirm_pending_settings(message_id)

		with self.assertRaises(frappe.ValidationError):
			confirm_pending_settings(message_id, decision="skip")
		self.assertEqual(frappe.db.get_single_value("Builder Settings", "home_page"), "bob-home")


class TestProposalsTheUserCannotApply(FrappeTestCase):
	def setUp(self):
		frappe.set_user(user_with_role("Website Manager"))

	def tearDown(self):
		frappe.set_user("Administrator")

	def assert_declined(self, out):
		self.assertTrue(out.startswith("DECLINED"), out)
		self.assertIn("isn't permitted", out)

	def test_create_doctype_is_declined_without_a_card(self):
		from builder.ai.agent.tools.data import request_create_doctype

		self.assert_declined(
			request_create_doctype(None, {"name": "Bob Visit Log", "fields": [{"fieldname": "title"}]})
		)

	def test_seed_sample_data_is_declined_without_a_card(self):
		from builder.ai.agent.tools.data import request_seed_sample_data

		self.assert_declined(
			request_seed_sample_data(None, {"doctype": "User", "rows": [{"email": "x@example.com"}]})
		)

	def test_connect_form_is_declined_without_a_card(self):
		from types import SimpleNamespace

		from builder.ai.agent.tools.forms import request_connect_form

		self.assert_declined(
			request_connect_form(
				SimpleNamespace(page_id="page-anything"), {"doctype_name": "Bob Visit Request"}
			)
		)
