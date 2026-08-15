from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.python import run_python


def run(script, page_id="the-open-page"):
	return run_python(SimpleNamespace(page_id=page_id), {"script": script})


class TestRunPython(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		# CI sites run with server scripts off, and the gate reads
		# common_site_config.json (not frappe.conf) — patch the gate itself, which
		# also covers safe_exec's own internal check.
		super().setUpClass()
		cls.sandbox_gate = patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True)
		cls.sandbox_gate.start()

	@classmethod
	def tearDownClass(cls):
		cls.sandbox_gate.stop()
		super().tearDownClass()

	def test_reads_records(self):
		out = run("result = frappe.db.count('Builder Page')")

		self.assertTrue(out.isdigit())

	def test_knows_the_sites_own_url(self):
		self.assertEqual(run("result = frappe.utils.get_url()"), frappe.utils.get_url())

	def test_exposes_the_open_page_id(self):
		self.assertEqual(run("result = page_id"), "the-open-page")

	def test_writes_do_not_persist(self):
		title = frappe.generate_hash(length=10)
		out = run(
			f"doc = frappe.get_doc({{'doctype': 'Builder Page', 'page_title': '{title}'}})\n"
			"doc.insert()\nresult = doc.name"
		)

		self.assertNotIn("FAILED", out)
		self.assertFalse(frappe.db.exists("Builder Page", {"page_title": title}))

	def test_blocks_imports(self):
		self.assertIn("FAILED", run("import os\nresult = os.getcwd()"))

	def test_blocks_raw_sql_and_direct_writes(self):
		self.assertIn("FAILED", run("result = frappe.db.sql('select 1')"))
		self.assertIn("FAILED", run("frappe.db.set_value('Builder Page', 'x', 'route', 'y')"))

	def test_nudges_when_result_is_never_assigned(self):
		self.assertIn("`result` was never assigned", run("x = 1"))

	def test_truncates_a_huge_result(self):
		out = run("result = ['x' * 100] * 200")

		self.assertLess(len(out), 7000)
		self.assertIn("truncated", out)

	def test_reads_answer_with_the_users_own_permissions(self):
		frappe.set_user("Guest")
		try:
			listed = run("result = frappe.get_all('User', pluck='name')")
			fetched = run("result = frappe.db.get_value('User', 'Administrator', 'email')")
			loaded = run("result = frappe.get_doc('User', 'Administrator').email")
		finally:
			frappe.set_user("Administrator")

		self.assertIn("FAILED", listed)
		self.assertIn("FAILED", fetched)
		self.assertIn("FAILED", loaded)
