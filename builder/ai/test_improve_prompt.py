from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.api import improve_prompt

PORTAL_USER = "bob-improve-prompt-portal@example.com"


class TestImprovePrompt(FrappeTestCase):
	def test_a_user_who_cannot_edit_pages_cannot_spend_the_key(self):
		if not frappe.db.exists("User", PORTAL_USER):
			frappe.get_doc({"doctype": "User", "email": PORTAL_USER, "first_name": "Portal"}).insert(
				ignore_permissions=True
			)
		with (
			self.set_user(PORTAL_USER),
			patch("builder.ai.llm.complete") as complete,
			self.assertRaises(frappe.ValidationError),
		):
			improve_prompt("a landing page for my bakery")

		complete.assert_not_called()
