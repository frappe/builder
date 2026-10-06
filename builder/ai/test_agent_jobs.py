from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.agent.loop import run_agent_job
from builder.ai.models import ModelRegistry

MODEL = {
	"name": "openrouter/test/model",
	"provider": "OpenRouter",
	"route_prefix": "openrouter",
	"litellm_provider": "openrouter",
	"api_base": None,
}
SECRET = "sk-or-secret"


class TestAgentJobs(FrappeTestCase):
	def enqueued_kwargs(self, call) -> dict:
		with (
			patch.object(ModelRegistry, "find", return_value=MODEL),
			patch("builder.ai.api.resolve_api_key", return_value=SECRET),
			patch("frappe.enqueue") as enqueue,
		):
			call()
		return enqueue.call_args.kwargs

	def assert_no_key(self, kwargs: dict):
		self.assertNotIn("api_key", kwargs)
		self.assertNotIn(SECRET, kwargs.values())

	def test_a_run_does_not_queue_the_api_key(self):
		page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Run"}).insert()

		self.assert_no_key(self.enqueued_kwargs(lambda: api.run("hi", page.name, model=MODEL["name"])))

	def test_a_resumed_run_does_not_queue_the_api_key(self):
		page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Resume"}).insert()
		session = frappe.get_doc(
			{"doctype": "Builder AI Session", "session_user": "Administrator", "page": page.name}
		).insert()

		self.assert_no_key(self.enqueued_kwargs(lambda: api.resume_after_action(session.name, "Applied.")))

	def test_the_job_resolves_its_own_key(self):
		with (
			patch("builder.ai.llm.resolve_api_key", return_value=SECRET),
			patch("builder.ai.agent.loop.AgentRunner") as runner,
		):
			run_agent_job("hi", MODEL["name"], page_id="some-page")

		runner.assert_called_once_with("hi", MODEL["name"], SECRET, page_id="some-page")
