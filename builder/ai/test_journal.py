import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from builder.ai import page_writer
from builder.ai.journal import TurnJournal, revert_since

ROOT = {
	"blockId": "root",
	"element": "div",
	"children": [{"blockId": "h1", "element": "h1", "innerHTML": "Old"}],
}


def make_session():
	page = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": f"Journal {frappe.generate_hash(length=6)}",
			"draft_blocks": frappe.as_json([ROOT]),
		}
	).insert()
	session = frappe.get_doc(
		{
			"doctype": "Builder AI Session",
			"page": page.name,
			"session_user": "Administrator",
			"status": "Active",
		}
	).insert()
	return session.name, page.name


def make_token(value: str):
	return frappe.get_doc(
		{
			"doctype": "Builder Token",
			"token_name": "Journal Test",
			"type": "Color",
			"value": value,
			"dark_value": "",
		}
	).insert(set_name=f"journal-{frappe.generate_hash(length=6)}")


def token_values(name: str) -> tuple:
	return tuple(frappe.db.get_value("Builder Token", name, ["value", "dark_value"]))


class TestTurnJournal(FrappeTestCase):
	def test_revert_restores_updates_recreates_deletions_and_removes_creations(self):
		session, _ = make_session()
		token = make_token("#000000")
		memory = frappe.get_doc({"doctype": "Builder AI Memory", "content": "journal fact"}).insert()
		since = now_datetime()
		with TurnJournal(session):
			token.value = "#ffffff"
			token.save()
			script = frappe.get_doc(
				{"doctype": "Builder Client Script", "script_type": "JavaScript", "script": "1"}
			).insert()
			frappe.delete_doc("Builder AI Memory", memory.name)

		self.assertEqual(revert_since(session, since), [])

		self.assertEqual(token_values(token.name)[0], "#000000")
		self.assertFalse(frappe.db.exists("Builder Client Script", script.name))
		self.assertEqual(frappe.db.get_value("Builder AI Memory", memory.name, "content"), "journal fact")

	def test_raw_column_writes_are_recorded(self):
		session, page = make_session()
		since = now_datetime()
		with TurnJournal(session):
			page_writer.save_draft_blocks(page, {**ROOT, "children": []})

		revert_since(session, since)

		self.assertEqual(frappe.parse_json(frappe.db.get_value("Builder Page", page, "draft_blocks")), [ROOT])

	def test_fields_the_turn_did_not_change_are_kept(self):
		session, _ = make_session()
		token = make_token("#000000")
		since = now_datetime()
		with TurnJournal(session):
			token.value = "#ffffff"
			token.save()
		token.reload()
		token.dark_value = "#111111"
		token.save()

		revert_since(session, since)

		self.assertEqual(token_values(token.name), ("#000000", "#111111"))

	def test_a_created_script_is_detached_before_it_is_deleted(self):
		session, page = make_session()
		since = now_datetime()
		with TurnJournal(session):
			script = frappe.get_doc(
				{"doctype": "Builder Client Script", "script_type": "JavaScript", "script": "1"}
			).insert()
			doc = frappe.get_doc("Builder Page", page)
			doc.append("client_scripts", {"builder_script": script.name})
			doc.save()

		self.assertEqual(revert_since(session, since), [])

		self.assertFalse(frappe.get_doc("Builder Page", page).client_scripts)
		self.assertFalse(frappe.db.exists("Builder Client Script", script.name))

	def test_later_turns_are_undone_too(self):
		session, _ = make_session()
		token = make_token("#000000")
		since = now_datetime()
		for value in ("#111111", "#222222"):
			with TurnJournal(session):
				token.reload()
				token.value = value
				token.save()

		revert_since(session, since)

		self.assertEqual(token_values(token.name)[0], "#000000")
		self.assertFalse(frappe.db.exists("Builder AI Change", {"session": session}))

	def test_bookkeeping_is_not_recorded(self):
		session, page = make_session()
		with TurnJournal(session) as journal:
			frappe.get_doc(
				{
					"doctype": "Builder Snapshot",
					"reference_doctype": "Builder Page",
					"reference_name": page,
					"snapshot_type": "Manual",
					"data": "{}",
				}
			).insert()
		self.assertEqual(journal.entries, {})
