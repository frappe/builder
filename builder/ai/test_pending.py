import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent import pending
from builder.ai.agent.tools import forms
from builder.ai.agent.tools.data import request_create_doctype, request_seed_sample_data
from builder.ai.agent.tools.python import run_python
from builder.ai.session import AISession


def user_with_role(role: str) -> str:
	email = f"bob-pending-{frappe.scrub(role).replace('_', '-')}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Bob Test", "roles": [{"role": role}]}
		).insert(ignore_permissions=True)
	return email


def form_payload(doctype: str) -> dict:
	return {
		"doctype_name": doctype,
		"fields": [{"fieldname": "email", "label": "Email", "fieldtype": "Data"}],
		"form_selector": "form",
	}


def drop_doctype(doctype: str) -> None:
	# Creating a DocType commits, so the test transaction can't roll it back.
	for web_form in frappe.get_all("Web Form", {"doc_type": doctype}, pluck="name"):
		frappe.delete_doc("Web Form", web_form, force=True)
	frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True)


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
	def test_a_website_manager_cannot_apply_what_desk_would_refuse(self):
		promoted = {
			"email": "bob-seeded@example.com",
			"first_name": "Seeded",
			"roles": [{"role": "System Manager"}],
		}
		for kind, payload in (
			("seed_sample_data", {"doctype": "User", "rows": [promoted]}),
			("create_doctype", {"name": "Bob Forbidden Type", "fields": [{"fieldname": "title"}]}),
			("connect_form", form_payload("Bob Forbidden Submission")),
		):
			with (
				self.subTest(kind=kind),
				self.set_user(user_with_role("Website Manager")),
				self.assertRaises(frappe.PermissionError),
			):
				pending.apply_pending_action(kind, payload)
		self.assertFalse(frappe.db.exists("User", "bob-seeded@example.com"))
		self.assertFalse(frappe.db.exists("DocType", "Bob Forbidden Type"))
		self.assertFalse(frappe.db.exists("DocType", "Bob Forbidden Submission"))

	def test_a_system_manager_can_create_seed_and_connect(self):
		suffix = frappe.generate_hash(length=6)
		doctype, form_doctype = f"Bob Seed Test {suffix}", f"Bob Connect Test {suffix}"
		self.addCleanup(drop_doctype, doctype)
		self.addCleanup(drop_doctype, form_doctype)

		with self.set_user(user_with_role("System Manager")):
			pending.apply_pending_action(
				"create_doctype", {"name": doctype, "fields": [{"fieldname": "title"}]}
			)
			pending.apply_pending_action(
				"seed_sample_data", {"doctype": doctype, "rows": [{"title": "Seeded"}]}
			)
			pending.apply_pending_action("connect_form", form_payload(form_doctype))

		self.assertTrue(frappe.db.exists(doctype, {"title": "Seeded"}))
		self.assertFalse(frappe.get_all("DocPerm", {"parent": doctype, "role": "Guest"}))
		self.assertTrue(frappe.db.exists("Web Form", {"doc_type": form_doctype}))

	def test_connect_form_will_not_wire_an_existing_doctype(self):
		with self.set_user(user_with_role("System Manager")), self.assertRaises(frappe.ValidationError):
			pending.apply_pending_action("connect_form", form_payload("User"))
		self.assertFalse(frappe.db.exists("Web Form", {"doc_type": "User", "login_required": 0}))


class TestProposals(FrappeTestCase):
	def test_a_website_manager_is_told_what_they_cannot_do(self):
		with self.set_user(user_with_role("Website Manager")):
			declined = [
				request_create_doctype(None, {"name": "Bob Visit Log", "fields": [{"fieldname": "title"}]}),
				request_seed_sample_data(None, {"doctype": "User", "rows": [{"email": "x@example.com"}]}),
				forms.request_connect_form(
					SimpleNamespace(page_id="page-x"), form_payload("Bob Visit Request")
				),
			]

		for out in declined:
			self.assertTrue(out.startswith("DECLINED") and "isn't permitted" in out, out)

	def test_reusing_what_exists_needs_no_create_permission(self):
		with self.set_user(user_with_role("Website Manager")):
			reused = request_create_doctype(
				None, {"name": "Builder Page", "fields": [{"fieldname": "title"}]}
			)
			with patch.object(forms, "connected_submission_doctype", return_value="Bob Visit Request"):
				connected = forms.request_connect_form(SimpleNamespace(page_id="page-x"), {})
			missing = forms.missing_create_permission("Builder Page")

		self.assertIn("already EXISTS", reused)
		self.assertTrue(connected.startswith("ALREADY CONNECTED"), connected)
		self.assertIsNone(missing)


class TestChatPrivacy(FrappeTestCase):
	def chat(self, user, page):
		with self.set_user(user):
			session = AISession.create({"page": page})
			return session.name, session.append_message("user", "hi")

	def test_a_website_manager_sees_only_their_own_chats(self):
		page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Chat privacy"}).insert().name
		manager = user_with_role("Website Manager")
		_, mine = self.chat(manager, page)
		_, theirs = self.chat(user_with_role("System Manager"), page)
		script = (
			f"m = 'Builder AI Message'\nresult = [frappe.db.get_value(m, '{mine}', 'content'), "
			f"frappe.db.get_value(m, '{theirs}', 'content'), frappe.db.exists(m, '{theirs}'), "
			f"frappe.db.count(m, {{'name': ['in', ['{mine}', '{theirs}']]}})]"
		)

		with self.set_user(manager), patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True):
			listed = frappe.get_list(
				"Builder AI Message", filters={"name": ["in", [mine, theirs]]}, pluck="name"
			)
			through_bob = run_python(SimpleNamespace(page_id=page), {"script": script})

		self.assertEqual(listed, [mine])
		self.assertEqual(json.loads(through_bob), ["hi", None, None, 1])

	def test_a_website_manager_cannot_write_into_a_chat(self):
		user = user_with_role("Website Manager")
		session = frappe.get_doc({"doctype": "Builder AI Session", "session_user": user}).insert()
		message = {
			"doctype": "Builder AI Message",
			"session": session.name,
			"role": "assistant",
			"content": "Apply?",
		}

		with self.set_user(user), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(message).insert()

	def test_deleting_a_page_removes_every_chat_on_it(self):
		manager = user_with_role("Website Manager")
		with self.set_user(manager):
			page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Shared chat page"}).insert().name
		session, _ = self.chat(user_with_role("System Manager"), page)

		with self.set_user(manager):
			frappe.delete_doc("Builder Page", page)

		self.assertFalse(frappe.db.exists("Builder AI Session", session))
