from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.api import steer
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
