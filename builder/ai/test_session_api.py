from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api
from builder.ai.session import AISession
from builder.utils import Block


class TestLazySessions(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Lazy Session Page",
				"draft_blocks": Block(element="div", originalElement="body").as_json(wrap_in_array=True),
			}
		).insert()

	def page_sessions(self) -> list[str]:
		return frappe.get_all(AISession.DOCTYPE, {"page": self.page.name}, pluck="name")

	def test_reading_a_page_without_chats_creates_nothing(self):
		result = api.get_ai_session(self.page.name, model="some/model")

		self.assertEqual(result["session_id"], "")
		self.assertEqual(result["messages"], [])
		self.assertEqual(self.page_sessions(), [])

	def test_reading_reopens_the_chat_that_was_talked_to(self):
		spoken = AISession.create({"page": self.page.name})
		spoken.append_message("user", "make it blue")
		AISession.create({"page": self.page.name})

		result = api.get_ai_session(self.page.name)

		self.assertEqual(result["session_id"], spoken.name)
		self.assertEqual(len(self.page_sessions()), 2)

	def test_first_message_creates_the_session(self):
		with (
			patch.object(api.ModelRegistry, "get_default", return_value="test/model"),
			patch.object(api.ModelRegistry, "is_known_model", return_value=True),
			patch.object(api, "resolve_api_key", return_value="key"),
			patch.object(api.frappe, "enqueue") as enqueue,
		):
			result = api.run("make it blue", self.page.name, model="test/model")

		session_id = result["session_id"]
		self.assertEqual(self.page_sessions(), [session_id])
		self.assertEqual(enqueue.call_args.kwargs["session_id"], session_id)
		messages = AISession.get(session_id).get_messages()
		self.assertEqual([(m["role"], m["content"]) for m in messages], [("user", "make it blue")])
