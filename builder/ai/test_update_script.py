from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.scripts import apply_update_script

PRICING_SCRIPT = "\n".join(
	f'document.querySelectorAll(".plan-{i}").forEach(function (el) {{ el.style.display = "block"; }});'
	for i in range(6)
)


def make_script(script: str = PRICING_SCRIPT):
	return frappe.get_doc(
		{"doctype": "Builder Client Script", "script_type": "JavaScript", "script": script}
	).insert()


def make_session() -> SimpleNamespace:
	session = frappe.get_doc(
		{"doctype": "Builder AI Session", "session_user": "Administrator", "status": "Active"}
	).insert()
	return SimpleNamespace(page_id=None, session_id=session.name)


def update(ctx, script, new_source: str) -> str:
	return apply_update_script(ctx, {"script_name": script.name, "script": new_source})


class TestUpdateScript(FrappeTestCase):
	def test_refuses_to_stub_a_script_from_before_the_session(self):
		script = make_script()
		ctx = make_session()

		out = update(ctx, script, "// Removed in this session.")

		self.assertTrue(out.startswith("FAILED"))
		self.assertEqual(frappe.db.get_value("Builder Client Script", script.name, "script"), PRICING_SCRIPT)

	def test_allows_clearing_a_script_created_this_session(self):
		ctx = make_session()
		script = make_script()

		out = update(ctx, script, "// Removed.")

		self.assertEqual(out, f"Updated script '{script.name}'.")

	def test_allows_an_edit_that_keeps_most_of_the_code(self):
		script = make_script()
		ctx = make_session()

		out = update(ctx, script, PRICING_SCRIPT.replace('"block"', '"flex"'))

		self.assertEqual(out, f"Updated script '{script.name}'.")
