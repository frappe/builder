import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import locks, page_writer
from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.page_changes import describe_user_changes, page_state

ROOT = {
	"blockId": "root",
	"element": "div",
	"children": [
		{"blockId": "title", "element": "h1", "innerHTML": "Title"},
		{"blockId": "intro", "element": "p", "innerHTML": "Intro"},
	],
}


def make_page() -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": f"User Edits {frappe.generate_hash(length=6)}",
				"draft_blocks": frappe.as_json([ROOT]),
			}
		)
		.insert()
		.name
	)


class TestUserEdits(FrappeTestCase):
	def test_edits_saved_mid_turn_survive_the_next_write(self):
		page = make_page()
		runner = AgentRunner("edit", "model", "key", user="Administrator", page_id=page)
		runner.load_page(page)
		try:
			op = {"tool_name": "update_block", "args": {"block_id": "title", "inner_text": "Bob's title"}}
			runner.apply_client_ops([op])
			edited = runner.tree.root | {
				"children": [
					runner.tree.root["children"][0],
					{**ROOT["children"][1], "innerHTML": "User intro"},
				]
			}
			page_writer.save_draft_blocks(page, edited)

			runner.absorb_user_edits()

			texts = [block["innerHTML"] for block in runner.tree.root["children"]]
			self.assertEqual(texts, ["Bob's title", "User intro"])
			self.assertIn("text 'Intro' -> 'User intro'", runner.user_edit_note)
		finally:
			for key, token in runner.held_locks:
				locks.release(key, token)

	def test_changes_since_the_last_turn_are_described(self):
		page = make_page()
		state = frappe.parse_json(frappe.as_json(page_state(page, ROOT, [])))
		edited = ROOT | {"children": [{**ROOT["children"][0], "innerHTML": "New title"}, ROOT["children"][1]]}
		frappe.db.set_value("Builder Page", page, "meta_description", "Changed by hand")

		lines = describe_user_changes(state, page, edited)

		self.assertIn("<h1> (ref title): text 'Title' -> 'New title'", lines)
		self.assertIn("page field meta_description changed", lines)
