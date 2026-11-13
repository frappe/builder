from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.agent.loop import AgentRunner, run_agent_job
from builder.ai.models import ModelRegistry
from builder.ai.test_llm import GATEWAY_MODEL
from builder.ai.test_llm import OPENROUTER_MODEL as MODEL

SECRET = "sk-or-secret"


def chat_session() -> tuple[str, str]:
	page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Bob job"}).insert().name
	session = frappe.get_doc({"doctype": "Builder AI Session", "session_user": "Administrator", "page": page})
	return page, session.insert().name


class TestAgentJobs(FrappeTestCase):
	def test_queued_jobs_never_carry_the_api_key(self):
		page, session = chat_session()
		for queue in (
			lambda: api.run("hi", page, model=MODEL["name"]),
			lambda: api.resume_after_action(session, "Applied."),
		):
			with (
				patch.object(ModelRegistry, "find", return_value=MODEL),
				patch("builder.ai.api.resolve_api_key", return_value=SECRET),
				patch("frappe.enqueue") as enqueue,
			):
				queue()

			self.assertNotIn("api_key", enqueue.call_args.kwargs)
			self.assertNotIn(SECRET, enqueue.call_args.kwargs.values())

	def test_a_resumed_turn_keeps_the_picked_effort(self):
		page, session = chat_session()
		with (
			patch.object(ModelRegistry, "find", return_value=MODEL),
			patch("builder.ai.api.resolve_api_key", return_value=SECRET),
			patch("frappe.enqueue") as enqueue,
		):
			api.run("hi", page, model=MODEL["name"], session_id=session, effort="xhigh")
			api.resume_after_action(session, "Applied.")

		self.assertEqual(
			[(c.kwargs["effort"], c.kwargs["timeout"]) for c in enqueue.call_args_list], [("xhigh", 3600)] * 2
		)

	def test_a_resume_without_a_key_queues_nothing(self):
		_, session = chat_session()

		with (
			patch("builder.ai.api.resolve_api_key", side_effect=frappe.ValidationError),
			patch("frappe.enqueue") as enqueue,
		):
			self.assertFalse(api.resume_after_action(session, "Applied."))
		enqueue.assert_not_called()

	def test_the_job_resolves_its_own_key(self):
		for queued in ({}, {"api_key": "sk-stale"}):
			with (
				self.subTest(queued=queued),
				patch("builder.ai.llm.resolve_api_key", return_value=SECRET),
				patch("builder.ai.agent.loop.AgentRunner") as runner,
			):
				run_agent_job("hi", MODEL["name"], page_id="some-page", **queued)

				runner.assert_called_once_with("hi", MODEL["name"], SECRET, page_id="some-page")

	def run_job_reporting_usage(self, turn) -> dict:
		page, session = chat_session()
		with (
			patch("builder.ai.llm.resolve_api_key", return_value=SECRET),
			patch.object(ModelRegistry, "find", return_value=MODEL),
			patch.object(AgentRunner, "run_turn", autospec=True, side_effect=turn),
			patch("builder.ai.agent.loop.capture") as capture,
		):
			try:
				run_agent_job("hi", MODEL["name"], page_id=page, session_id=session, user="Administrator")
			except RuntimeError:
				pass

		capture.assert_called_once()
		self.assertEqual(capture.call_args.args, ("builder_ai_used", "builder"))
		self.assertEqual(capture.call_args.kwargs["user"], "Administrator")
		return capture.call_args.kwargs["properties"]

	def test_a_finished_turn_reports_its_ai_usage(self):
		def turn(runner, started):
			op = {"tool_name": "generate_page", "args": {}}
			runner.record_round(0, [op, {"tool_name": "preview_page", "args": {}}], "")
			runner.applied_operations.append(op)
			runner.outcome = "complete"

		usage = self.run_job_reporting_usage(turn)

		self.assertEqual(usage["outcome"], "complete")
		self.assertEqual((usage["provider"], usage["model"]), ("openrouter", MODEL["name"].split("/", 1)[1]))
		self.assertEqual(usage["tools"], ["generate_page", "preview_page"])
		self.assertTrue(usage["generated_page"])
		self.assertEqual((usage["operations"], usage["rounds"]), (1, 1))

	def test_a_turn_that_crashes_is_still_reported(self):
		def turn(runner, started):
			raise RuntimeError("worker died")

		self.assertEqual(self.run_job_reporting_usage(turn)["outcome"], "failed")

	def test_usage_never_names_a_custom_gateway(self):
		with patch.object(ModelRegistry, "find", return_value=GATEWAY_MODEL):
			self.assertEqual(ModelRegistry.telemetry_route(GATEWAY_MODEL["name"]), ("custom", "llama-4"))

	def test_broken_telemetry_does_not_fail_the_turn(self):
		runner = AgentRunner("hi", model=MODEL["name"], api_key=SECRET)
		with patch("builder.ai.agent.loop.capture", side_effect=RuntimeError("pulse down")):
			runner.capture_usage()
