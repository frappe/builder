import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api, turns
from builder.ai.agent.loop import run_agent_job
from builder.ai.models import ModelRegistry
from builder.ai.session import AISession
from builder.ai.site_key import UsageLimitError
from builder.ai.test_agent_jobs import chat_session
from builder.ai.test_llm import OPENROUTER_MODEL as MODEL
from builder.ai.turns import TurnQueue

SPENT = "This site has used today's AI allowance."


class TurnsTestCase(FrappeTestCase):
	def setUp(self):
		# keys of their own, so a test never touches the site's real tickets
		suffix = frappe.generate_hash(length=6)
		self.enterContext(patch.object(turns, "TICKETS_KEY", f"builder_ai_turn_tickets_test_{suffix}"))
		self.enterContext(patch.object(turns, "FRONT_KEY", f"builder_ai_turns_at_front_test_{suffix}"))
		self.addCleanup(frappe.cache.delete, TurnQueue.key(turns.TICKETS_KEY), TurnQueue.key(turns.FRONT_KEY))


class TestTurnTickets(TurnsTestCase):
	def test_a_site_gets_as_many_tickets_as_it_may_have_turns(self):
		tickets = [TurnQueue.claim(600) for _ in range(turns.DEFAULT_TURNS_IN_FLIGHT)]
		self.assertTrue(all(tickets))
		self.assertIsNone(TurnQueue.claim(600))
		TurnQueue.release(tickets[0])
		self.assertTrue(TurnQueue.claim(600))

	def test_site_config_sets_how_many(self):
		with patch.dict(frappe.local.conf, {"builder_ai_turns_in_flight": 1}):
			self.assertTrue(TurnQueue.claim(600))
			self.assertIsNone(TurnQueue.claim(600))

	def test_turns_sent_side_by_side_cannot_take_more_tickets(self):
		key = TurnQueue.key(turns.TICKETS_KEY)

		def claim(n):
			now = time.time()
			return frappe.cache.eval(turns.CLAIM, 1, key, now, 3, now + 600, f"t{n}", 600)

		with ThreadPoolExecutor(max_workers=20) as pool:
			claimed = list(pool.map(claim, range(40)))
		self.assertEqual(sum(claimed), 3)

	def test_a_ticket_lapses_once_its_job_cannot_still_be_running(self):
		with patch.object(turns, "QUEUE_WAIT", -60):
			for _ in range(turns.DEFAULT_TURNS_IN_FLIGHT):
				TurnQueue.claim(0)
		self.assertEqual(TurnQueue.in_flight(), 0)
		self.assertTrue(TurnQueue.claim(600))

	def test_a_request_that_fails_gives_its_ticket_back(self):
		TurnQueue.claim(600)
		self.assertEqual(TurnQueue.in_flight(), 1)
		frappe.db.rollback()
		self.assertEqual(TurnQueue.in_flight(), 0)

	def test_only_so_many_turns_go_to_the_front(self):
		first = [TurnQueue.goes_first() for _ in range(turns.FRONT_TURNS + 2)]
		self.assertEqual(first, [True] * turns.FRONT_TURNS + [False, False])


class TestQueueingATurn(TurnsTestCase):
	def setUp(self):
		super().setUp()
		self.page, self.session = chat_session()
		self.enterContext(patch.object(ModelRegistry, "find", return_value=MODEL))
		self.enterContext(patch("builder.ai.api.resolve_api_key", return_value="sk-key"))
		self.enqueue = self.enterContext(patch("frappe.enqueue"))

	def sessions(self) -> int:
		return frappe.db.count(AISession.DOCTYPE, {"page": self.page})

	def test_a_turn_goes_first_and_carries_its_ticket(self):
		api.run("hi", self.page, model=MODEL["name"])
		job = self.enqueue.call_args.kwargs
		self.assertTrue(job["at_front"])
		self.assertEqual(TurnQueue.in_flight(), 1)
		self.assertTrue(job["turn_ticket"])

	def test_a_turn_goes_to_the_queue_site_config_names_once_the_bench_declares_it(self):
		queues = "frappe.utils.background_jobs.get_queues_timeout"
		builtin = {"short": 300, "default": 300, "long": 1500}
		with (
			patch.dict(frappe.local.conf, {"builder_ai_queue": "builder_ai_test"}),
			patch.object(turns, "has_worker", return_value=True),
		):
			with patch(queues, return_value={**builtin, "builder_ai_test": 3660}):
				api.run("hi", self.page, model=MODEL["name"])
			self.assertEqual(self.enqueue.call_args.kwargs["queue"], "builder_ai_test")
			# a queue no worker config declares has no worker either: such a turn would wait forever
			with patch(queues, return_value=builtin):
				api.run("hi", self.page, model=MODEL["name"])
			self.assertEqual(self.enqueue.call_args.kwargs["queue"], turns.DEFAULT_QUEUE)

	def test_a_turn_goes_to_the_default_queue_while_no_worker_serves_the_named_one(self):
		queues = "frappe.utils.background_jobs.get_queues_timeout"
		declared = {"short": 300, "default": 300, "long": 1500, "builder_ai_test": 3660}
		with (
			patch.dict(frappe.local.conf, {"builder_ai_queue": "builder_ai_test"}),
			patch(queues, return_value=declared),
		):
			# nothing listens on builder_ai_test: RQ knows of no worker for it
			api.run("hi", self.page, model=MODEL["name"])
			self.assertEqual(self.enqueue.call_args.kwargs["queue"], turns.DEFAULT_QUEUE)
			with patch.object(turns, "has_worker", return_value=True):
				api.run("hi", self.page, model=MODEL["name"])
			self.assertEqual(self.enqueue.call_args.kwargs["queue"], "builder_ai_test")

	def test_a_turn_on_the_site_key_holds_a_worker_no_longer_than_the_host_allows(self):
		with (
			patch("builder.ai.site_key.is_site_key", return_value=True),
			patch("builder.ai.site_key.allowance", return_value=None),
			patch.dict(frappe.local.conf, {"builder_ai_site_key_max_effort": "high"}),
		):
			api.run("hi", self.page, model=MODEL["name"], effort="xhigh")
		job = self.enqueue.call_args.kwargs
		self.assertEqual((job["effort"], job["timeout"]), ("high", 1800))

	def test_a_queue_has_a_worker_while_rq_knows_a_live_one(self):
		with patch("frappe.utils.background_jobs.get_workers", return_value=[object()]) as workers:
			self.assertTrue(turns.has_worker("long"))
		self.assertTrue(workers.call_args.args[0].name.endswith(":long"))
		with patch("frappe.utils.background_jobs.get_workers", return_value=[]):
			self.assertFalse(turns.has_worker("long"))

	def test_a_site_with_every_turn_queued_is_refused_before_anything_is_saved(self):
		for _ in range(turns.DEFAULT_TURNS_IN_FLIGHT):
			api.run("hi", self.page, model=MODEL["name"])
		sessions = self.sessions()
		with self.assertRaises(frappe.TooManyRequestsError):
			api.run("one more", self.page, model=MODEL["name"])
		self.assertEqual(self.enqueue.call_count, turns.DEFAULT_TURNS_IN_FLIGHT)
		self.assertEqual(self.sessions(), sessions)

	def test_a_spent_allowance_refuses_the_turn_before_it_is_queued(self):
		with (
			patch("builder.ai.site_key.is_site_key", return_value=True),
			patch("builder.ai.site_key.allowance") as allowance,
			self.assertRaises(UsageLimitError) as refused,
		):
			allowance.return_value.check.side_effect = UsageLimitError(SPENT)
			api.run("hi", self.page, model=MODEL["name"])
		self.assertEqual(str(refused.exception), SPENT)
		self.enqueue.assert_not_called()
		self.assertEqual((self.sessions(), TurnQueue.in_flight()), (1, 0))

	def test_a_resumed_turn_that_cannot_be_queued_says_why_in_the_chat(self):
		with patch.dict(frappe.local.conf, {"builder_ai_turns_in_flight": 1}):
			TurnQueue.claim(600)
			self.assertFalse(api.resume_after_action(self.session, "Applied."))
		self.enqueue.assert_not_called()
		last = AISession.get(self.session).get_messages()[-1]
		self.assertIn("already working on 1 requests", last["content"])

	def test_the_job_gives_its_ticket_back_when_it_ends(self):
		ticket = TurnQueue.claim(600)
		with (
			patch("builder.ai.llm.resolve_api_key", return_value="sk-key"),
			patch("builder.ai.agent.loop.AgentRunner.run", side_effect=RuntimeError("model down")),
		):
			with self.assertRaises(RuntimeError):
				run_agent_job("hi", MODEL["name"], turn_ticket=ticket, page_id=self.page)
		self.assertEqual(TurnQueue.in_flight(), 0)

	def test_the_next_build_takes_over_the_ticket_of_the_turn_that_queued_it(self):
		with patch.dict(frappe.local.conf, {"builder_ai_turns_in_flight": 1}):
			ticket = TurnQueue.claim(600)
			builds = [{"page_id": self.page, "title": "About", "route": "/about", "brief": "b"}]
			self.assertTrue(api.queue_page_build(self.session, builds, turn_ticket=ticket))
		self.assertEqual(self.enqueue.call_args.kwargs["turn_ticket"], ticket)
		self.assertEqual(TurnQueue.in_flight(), 1)
