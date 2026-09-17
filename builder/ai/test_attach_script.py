from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.scripts import apply_attach_page_script


def make_page():
	return frappe.get_doc({"doctype": "Builder Page", "page_title": "Attach Test", "blocks": "[]"}).insert()


def make_script():
	return frappe.get_doc(
		{"doctype": "Builder Client Script", "script_type": "CSS", "script": ".hero { opacity: 1; }"}
	).insert()


def attached_scripts(page_id: str) -> list[str]:
	return frappe.db.get_all(
		"Builder Page Client Script",
		filters={"parent": page_id, "parenttype": "Builder Page"},
		pluck="builder_script",
	)


class TestAttachPageScript(FrappeTestCase):
	def test_attaches_an_existing_script(self):
		page, script = make_page(), make_script()
		args = {"script_name": script.name}
		out = apply_attach_page_script(SimpleNamespace(page_id=page.name), args)
		self.assertIn("Attached shared CSS script", out)
		self.assertEqual(attached_scripts(page.name), [script.name])
		# The op is enriched with the content so the canvas script list can mirror it.
		self.assertEqual(args["script_type"], "CSS")
		self.assertEqual(args["script"], script.script)

	def test_attach_is_idempotent(self):
		page, script = make_page(), make_script()
		ctx = SimpleNamespace(page_id=page.name)
		apply_attach_page_script(ctx, {"script_name": script.name})
		out = apply_attach_page_script(ctx, {"script_name": script.name})
		self.assertIn("already attached", out)
		self.assertEqual(attached_scripts(page.name), [script.name])

	def test_unknown_script_fails(self):
		page = make_page()
		out = apply_attach_page_script(SimpleNamespace(page_id=page.name), {"script_name": "nope"})
		self.assertTrue(out.startswith("FAILED"))
		self.assertEqual(attached_scripts(page.name), [])

	def test_no_open_page_fails(self):
		out = apply_attach_page_script(SimpleNamespace(page_id=None), {"script_name": "anything"})
		self.assertTrue(out.startswith("FAILED"))
