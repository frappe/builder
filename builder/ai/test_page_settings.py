from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.settings import set_page_settings


def make_page(**fields):
	return frappe.get_doc({"doctype": "Builder Page", "page_title": "Settings Test", **fields}).insert()


class TestSetPageSettings(FrappeTestCase):
	def set_route(self, page, route):
		return set_page_settings(SimpleNamespace(page_id=page.name), {"route": route})

	def test_dynamic_route_is_flagged_and_explained(self):
		page = make_page()

		out = self.set_route(page, "partners/<partner_id>")

		self.assertIn("DYNAMIC", out)
		self.assertIn("frappe.form_dict.partner_id", out)
		self.assertEqual(frappe.db.get_value("Builder Page", page.name, "dynamic_route"), 1)

	def test_colon_params_work_too(self):
		page = make_page()

		out = self.set_route(page, "cases/:case_id")

		self.assertIn("frappe.form_dict.case_id", out)
		self.assertEqual(frappe.db.get_value("Builder Page", page.name, "dynamic_route"), 1)

	def test_static_route_gets_no_dynamic_note(self):
		page = make_page()

		out = self.set_route(page, f"plain-{page.name}")

		self.assertNotIn("DYNAMIC", out)
		self.assertEqual(frappe.db.get_value("Builder Page", page.name, "dynamic_route"), 0)

	def test_refuses_a_route_another_page_owns(self):
		owner = make_page(route="taken-route")
		page = make_page()

		out = self.set_route(page, "taken-route")

		self.assertIn("FAILED", out)
		self.assertIn(owner.name, out)
		self.assertIn("hierarchy", out)
