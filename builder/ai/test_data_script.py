from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.data import write_page_data_script


class Ctx:
	def __init__(self, page_id):
		self.page_id = page_id


class TestWriteDataScript(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Data Script Page"}).insert()
		self.ctx = Ctx(self.page.name)

	def write(self, script, safe_exec_enabled):
		with patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=safe_exec_enabled):
			return write_page_data_script(self.ctx, {"script": script})

	def saved_script(self):
		return frappe.db.get_value("Builder Page", self.page.name, "page_data_script")

	def test_refuses_names_missing_when_server_scripts_are_off(self):
		out = self.write("data.events = frappe.get_list('Event', fields=['subject'])", False)

		self.assertIn("frappe.get_list", out)
		self.assertTrue(out.startswith("FAILED"))
		self.assertFalse(self.saved_script())

	def test_keeps_names_that_work_on_every_site(self):
		script = (
			"data.events = frappe.db.get_all('Event', fields=['subject'])\n"
			"data.partner = frappe.get_doc('User', frappe.form_dict.user_id)"
		)

		out = self.write(script, False)

		self.assertFalse(out.startswith("FAILED"), out)
		self.assertEqual(self.saved_script(), script)

	def test_ignores_names_in_comments_and_strings(self):
		script = (
			"# frappe.utils.getdate would be handy here\n"
			"data.note = 'see frappe.get_list'\n"
			"data.events = frappe.db.get_all('Event', fields=['subject'])"
		)

		self.assertFalse(self.write(script, False).startswith("FAILED"))

	def test_refuses_a_script_that_does_not_parse(self):
		out = self.write("data.events = frappe.get_list('Event'", False)

		self.assertTrue(out.startswith("FAILED"))
		self.assertFalse(self.saved_script())

	def test_allows_the_full_namespace_when_server_scripts_are_on(self):
		script = "data.events = frappe.get_list('Event', fields=['subject'])"

		self.assertFalse(self.write(script, True).startswith("FAILED"))
