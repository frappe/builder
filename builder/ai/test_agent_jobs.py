from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.agent.loop import run_agent_job
from builder.ai.models import ModelRegistry
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
