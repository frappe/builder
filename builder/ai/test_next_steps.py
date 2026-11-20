from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import llm
from builder.ai.agent import next_steps
from builder.ai.agent.loop import AgentRunner
from builder.ai.session import AISession
from builder.ai.test_page_changes import chunk, heading, make_page

REPLY = "Moved the class schedule above the story."
STEPS = "\n\n<next>Add a booking form that saves entries</next>\n<next>Show prices beside each class</next>"


class TestSplitNextSteps(FrappeTestCase):
	def test_takes_the_steps_off_the_reply(self):
		text, steps = next_steps.split(REPLY + STEPS)

		self.assertEqual(text, REPLY)
		self.assertEqual(steps, ["Add a booking form that saves entries", "Show prices beside each class"])

	def test_keeps_three_steps_short_enough_for_a_button(self):
		tags = "".join(f"<next>Step {n}</next>" for n in range(5)) + f"<next>{'long ' * 30}</next>"

		self.assertEqual(next_steps.split(tags)[1], ["Step 0", "Step 1", "Step 2"])

	def test_an_unclosed_last_step_still_counts(self):
		self.assertEqual(next_steps.split("Done.\n<next>Tighten the footer")[1], ["Tighten the footer"])

	def test_a_reply_without_steps_is_left_alone(self):
		self.assertEqual(next_steps.split(REPLY), (REPLY, []))


class TestNextStepsInATurn(FrappeTestCase):
	"""The steps never reach the chat as text: the stream stops short of them, and the
	saved reply carries them as metadata the chat shows as buttons."""

	def setUp(self):
		tag = frappe.generate_hash(length=6)
		self.page = make_page("Studio", f"next-steps-{tag}", [heading("studiohead", "Stillwater")])
		self.session_id = AISession.create({"page": self.page}).name
		self.streamed = []

	def run_turn(self, *pieces: str) -> dict:
		def record(event, message, **kwargs):
			if event.startswith("ai_chat_stream") and not message.get("kind"):
				self.streamed.append(message)

		reply = iter([chunk(content=piece) for piece in pieces] + [chunk(finish_reason="stop")])
		runner = AgentRunner("tidy the page", "m", "k", page_id=self.page, session_id=self.session_id)
		with (
			patch.object(llm, "complete_with_tools", lambda *a, **k: reply),
			patch("frappe.publish_realtime", record),
			patch.object(AgentRunner, "maybe_name_session"),
		):
			runner.run()
		return AISession.get(self.session_id).get_messages()[-1]

	def shown(self) -> str:
		text = ""
		for message in self.streamed:
			text = message["chunk"] if message.get("replace") else text + message["chunk"]
		return text

	def test_streams_the_reply_and_saves_the_steps_apart(self):
		saved = self.run_turn(REPLY, "\n\n<ne", "xt>Add a booking form that saves entries</next>")

		self.assertEqual(self.shown().strip(), REPLY)
		self.assertEqual(saved["content"], REPLY)
		self.assertEqual(saved["metadata"]["suggestions"], ["Add a booking form that saves entries"])

	def test_a_held_back_bracket_is_released_when_it_is_not_a_tag(self):
		saved = self.run_turn("Classes from ₹800 <", " ₹1,200.")

		self.assertEqual(self.shown(), "Classes from ₹800 < ₹1,200.")
		self.assertNotIn("suggestions", saved["metadata"])
