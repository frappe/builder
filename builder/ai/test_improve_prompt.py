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
		frappe.set_user(PORTAL_USER)
		try:
			with patch("builder.ai.llm.complete") as complete, self.assertRaises(frappe.ValidationError):
				improve_prompt("a landing page for my bakery")
		finally:
			frappe.set_user("Administrator")

		complete.assert_not_called()

	def test_a_page_editor_gets_the_rewrite(self):
		with (
			patch("builder.ai.api.resolve_api_key", return_value="key"),
			patch("builder.ai.llm.complete", return_value=" A sharper prompt "),
		):
			self.assertEqual(improve_prompt("a landing page for my bakery"), "A sharper prompt")
