from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import llm
from builder.ai.agent.loop import AgentRunner, CancelledError, NotesSentNow
from builder.ai.api import steer, take_back_notes
from builder.ai.session import AISession


class TestSteer(FrappeTestCase):
	def setUp(self):
		self.session_id = AISession.create({"page": None})._doc.name

	def tearDown(self):
		AISession.clear_notes(self.session_id)

	def test_queues_a_note_only_while_a_turn_runs(self):
		self.assertEqual(steer(self.session_id, "warmer colours")["status"], "not_running")

		token = AISession.start_run(self.session_id)
		try:
			self.assertEqual(steer(self.session_id, "  warmer colours ")["status"], "queued")
			self.assertEqual(steer(self.session_id, "  ")["status"], "not_running")
		finally:
			AISession.end_run(self.session_id, token)

		self.assertEqual(AISession.pop_notes(self.session_id), ["warmer colours"])

	def test_the_loop_reads_notes_in_and_saves_them(self):
		for note in ("first", "second"):
			AISession.queue_note(self.session_id, note)
		runner = AgentRunner("hi", model="m", api_key="k", session_id=self.session_id, effort="high")
		messages = []

		runner.read_notes(messages)

		self.assertEqual([m["content"].splitlines()[-1] for m in messages], ["first", "second"])
		saved = [m["content"] for m in AISession.get(self.session_id).get_messages()]
		self.assertEqual(saved, ["first", "second"])
		self.assertEqual(AISession.latest_turn_metadata(self.session_id)["effort"], "high")
		self.assertEqual(AISession.pop_notes(self.session_id), [])

	def test_send_now_asks_the_running_turn_to_read_its_notes(self):
		self.assertEqual(steer(self.session_id, now=True)["status"], "not_running")

		token = AISession.start_run(self.session_id)
		try:
			self.assertEqual(steer(self.session_id, now=True)["status"], "queued")
		finally:
			AISession.end_run(self.session_id, token)

		self.assertTrue(AISession.notes_wanted_now(self.session_id))
		AISession.pop_notes(self.session_id)
		self.assertFalse(AISession.notes_wanted_now(self.session_id))

	def test_take_back_hands_over_only_unread_notes(self):
		for note in ("first", "second"):
			AISession.queue_note(self.session_id, note)
		AISession.send_notes_now(self.session_id)

		self.assertEqual(take_back_notes(self.session_id), {"notes": ["first", "second"]})
		self.assertEqual(take_back_notes(self.session_id), {"notes": []})
		self.assertFalse(AISession.notes_wanted_now(self.session_id))

	def test_a_cancel_ends_the_turn_and_notes_sent_now_end_the_step(self):
		runner = AgentRunner("hi", model="m", api_key="k", session_id=self.session_id)
		self.assertIsNone(runner.stop_requested())

		AISession.send_notes_now(self.session_id)
		self.assertIsInstance(runner.stop_requested(), NotesSentNow)

		frappe.cache.set_value(runner.cancel_key(), 1)
		try:
			self.assertIsInstance(runner.stop_requested(), CancelledError)
		finally:
			runner.clear_cancel_flag()

	def test_notes_sent_now_drop_the_step_being_streamed(self):
		runner = AgentRunner("hi", model="m", api_key="k", session_id=self.session_id)
		stream = MagicMock()
		stream.__iter__.return_value = iter([MagicMock()])
		AISession.send_notes_now(self.session_id)

		with patch.object(llm, "complete_with_tools", return_value=stream):
			self.assertRaises(NotesSentNow, runner.call_tool_llm, [])

		stream.close.assert_called_once()
		self.assertEqual(runner.stream_retries, 0)
