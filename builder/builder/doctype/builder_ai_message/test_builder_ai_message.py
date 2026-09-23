import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBuilderAIMessage(FrappeTestCase):
	def test_metadata_with_markup_stays_valid_json(self):
		session = frappe.get_doc(
			{"doctype": "Builder AI Session", "session_user": "Administrator", "status": "Active"}
		).insert()
		trace = {"trace": [{"tools": [{"args": '{"inner_html": "<svg viewBox=\\"0 0 4 4\\"></svg>"}'}]}]}

		message = frappe.get_doc(
			{
				"doctype": "Builder AI Message",
				"session": session.name,
				"role": "assistant",
				"content": "Done.",
				"metadata_json": json.dumps(trace),
			}
		).insert()

		self.assertEqual(json.loads(message.reload().metadata_json), trace)
