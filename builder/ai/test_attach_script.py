from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner, activity_summary
from builder.ai.agent.tools.scripts import (
	apply_attach_page_script,
	apply_detach_page_script,
	apply_update_script,
)


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


class TestUpdateScript(FrappeTestCase):
	def test_updates_a_script_attached_to_the_page(self):
		page, script = make_page(), make_script()
		ctx = SimpleNamespace(page_id=page.name)
		apply_attach_page_script(ctx, {"script_name": script.name})

		out = apply_update_script(ctx, {"script_name": script.name, "script": ".hero { opacity: 0; }"})

		self.assertTrue(out.startswith(f"Updated script '{script.name}'."), out)
		self.assertIn("live", out)
		self.assertEqual(
			frappe.db.get_value("Builder Client Script", script.name, "script"), ".hero { opacity: 0; }"
		)

	def test_only_touches_a_script_on_the_open_page(self):
		page, script = make_page(), make_script()
		for page_id in (page.name, None):
			out = apply_update_script(
				SimpleNamespace(page_id=page_id), {"script_name": script.name, "script": ".a {}"}
			)

			self.assertTrue(out.startswith("FAILED"), page_id)
		self.assertEqual(frappe.db.get_value("Builder Client Script", script.name, "script"), script.script)


class TestDetachPageScript(FrappeTestCase):
	def test_unlinks_the_script_and_keeps_the_doc(self):
		page, script = make_page(), make_script()
		ctx = SimpleNamespace(page_id=page.name)
		apply_attach_page_script(ctx, {"script_name": script.name})

		out = apply_detach_page_script(ctx, {"script_name": script.name})

		self.assertTrue(out.startswith(f"Removed script '{script.name}'"), out)
		self.assertEqual(attached_scripts(page.name), [])
		self.assertTrue(frappe.db.exists("Builder Client Script", script.name))

	def test_refuses_a_script_the_page_does_not_carry(self):
		page, script = make_page(), make_script()
		for page_id in (page.name, None):
			out = apply_detach_page_script(SimpleNamespace(page_id=page_id), {"script_name": script.name})

			self.assertTrue(out.startswith("FAILED"), page_id)

	def test_reads_as_a_removal_in_the_chat(self):
		self.assertEqual(
			activity_summary("detach_page_script", {"script_name": "Hero Motion"}),
			"Removed script: Hero Motion",
		)
		self.assertEqual(
			AgentRunner.describe_operations([{"tool_name": "detach_page_script"}]), "Removed a script"
		)
