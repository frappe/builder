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

	def write(self, script, safe_exec_enabled=True):
		with (
			patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=safe_exec_enabled),
			patch("builder.utils.is_safe_exec_enabled", return_value=safe_exec_enabled),
		):
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


class TestDataScriptTrial(FrappeTestCase):
	"""The script runs once before it saves, so a broken one never reaches the published page."""

	def setUp(self):
		self.page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Trial Page"}).insert()
		self.ctx = Ctx(self.page.name)

	def write(self, script):
		return TestWriteDataScript.write(self, script)

	def saved_script(self):
		return frappe.db.get_value("Builder Page", self.page.name, "page_data_script")

	def test_saves_a_script_that_runs(self):
		out = self.write("data.total = len([1, 2])")

		self.assertTrue(out.startswith("Saved"), out)
		self.assertNotIn("test run", out)
		self.assertEqual(self.saved_script(), "data.total = len([1, 2])")

	def test_refuses_unpacking_in_an_assignment(self):
		out = self.write("data.year = 1\ny, m, d = '2026-05-03'.split('-')")

		self.assertTrue(out.startswith("FAILED"), out)
		self.assertIn("line 2: y, m, d = '2026-05-03'.split('-')", out)
		self.assertIn("NameError: name '_unpack_sequence_' is not defined", out)
		self.assertFalse(self.saved_script())

	def test_forwards_every_script_frame_of_the_error(self):
		out = self.write("rows = [1, 2]\ndef count():\n    return len(rows)\ndata.total = count()")

		self.assertTrue(out.startswith("FAILED"), out)
		self.assertIn(
			"  line 4: data.total = count()\n  line 3: return len(rows)\nNameError: name 'rows' is not defined",
			out,
		)
		self.assertFalse(self.saved_script())

	def test_a_missing_request_param_only_warns(self):
		script = "data.slug = frappe.form_dict.slug.upper()"

		out = self.write(script)

		self.assertTrue(out.startswith("Saved"), out)
		self.assertIn("A test run without URL or query params raised", out)
		self.assertEqual(self.saved_script(), script)
