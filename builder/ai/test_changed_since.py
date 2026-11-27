from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import llm
from builder.ai.agent.loop import AgentRunner
from builder.ai.api import confirm_pending_settings
from builder.ai.page_writer import load_page_root, save_draft_blocks
from builder.ai.session import AISession
from builder.ai.test_page_changes import ScriptedModel, heading, make_page

CHANGED = "This page has changed outside this chat"


class TestChangedSince(FrappeTestCase):
	def setUp(self):
		tag = frappe.generate_hash(length=6)
		self.page = make_page("Home", f"cs-home-{tag}", [heading("cshead", "Welcome")])
		self.other = make_page("About", f"cs-about-{tag}", [heading("csabout", "About us")])
		self.session_id = AISession.create({"page": self.page}).name

	def turn(self, *rounds, page_id: str | None = None) -> str:
		"""Run a turn and return the context its first round was sent."""
		model = ScriptedModel(*rounds)
		sent = []

		def complete(model_id, messages, *args, **kwargs):
			sent.append(messages[-3]["content"])
			return model()

		runner = AgentRunner("go", "m", "k", page_id=page_id or self.page, session_id=self.session_id)
		with (
			patch.object(llm, "complete_with_tools", complete),
			patch("frappe.publish_realtime"),
			patch.object(AgentRunner, "maybe_name_session"),
		):
			runner.run()
		return sent[0]

	def edit_by_hand(self, page_id: str, text: str) -> None:
		root = load_page_root(page_id)
		root["children"][0]["innerHTML"] = text
		save_draft_blocks(page_id, root)

	def test_an_edit_made_since_the_last_turn_is_called_out(self):
		first = self.turn([("edit_page", {"ops": '@cshead "Hello"'})], "Done.")
		self.edit_by_hand(self.page, "Hi there")

		self.assertNotIn(CHANGED, first)
		self.assertIn(CHANGED, self.turn("Done."))
		self.assertNotIn(CHANGED, self.turn("Done."))

	def test_the_editor_saving_its_copy_of_an_unchanged_page_is_not_an_edit(self):
		self.turn([("edit_page", {"ops": '@cshead "Hello"'})], "Done.")
		root = load_page_root(self.page)
		for block in (root, *root["children"]):
			block.update(mobileStyles={}, tabletStyles={}, attributes={}, classes=[], customAttributes={})
		save_draft_blocks(self.page, root)

		self.assertNotIn(CHANGED, self.turn("Done."))

	def test_a_page_deleted_while_bob_works_still_ends_the_turn(self):
		"""The turn's end marks its page; the user may have deleted it in the desk meanwhile"""
		model, events = ScriptedModel("Done."), []

		def complete(*args, **kwargs):
			frappe.db.delete("Builder Page", self.page)
			return model()

		runner = AgentRunner("go", "m", "k", page_id=self.page, session_id=self.session_id)
		with (
			patch.object(llm, "complete_with_tools", complete),
			patch("frappe.publish_realtime", lambda event, *args, **kwargs: events.append(event)),
			patch.object(AgentRunner, "maybe_name_session"),
		):
			runner.run()

		saved = AISession.get(self.session_id).get_messages()[-1]
		self.assertEqual((saved["content"], saved["metadata"]["status"]), ("Done.", "complete"))
		self.assertIn(f"ai_chat_complete_{self.page}", events)
		self.assertIsNone(load_page_root(self.page))
		for end in (runner.emit_cancelled, lambda: runner.fail_turn("Something broke.")):
			end()
			marks = AISession.get(self.session_id).get_messages()[-1]["metadata"]["pageMarks"]
			self.assertIn(self.page, marks)

	def test_an_approved_edit_to_another_page_is_not_taken_for_the_users(self):
		self.turn("Hi.", page_id=self.other)
		self.turn([("edit_page", {"page": self.other, "ops": '@csabout "Our story"'})], "Ready.")
		card = AISession.get(self.session_id).get_messages()[-1]
		with patch("frappe.enqueue"):
			confirm_pending_settings(card["id"], "apply")

		self.assertNotIn(CHANGED, self.turn("Done.", page_id=self.other))
