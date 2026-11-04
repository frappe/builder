from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.components import run_edit_component
from builder.builder.component_versions import ensure_component_version, resolve_component


def make_component():
	block = {
		"blockId": "nav",
		"element": "nav",
		"children": [{"blockId": "link", "element": "a", "innerHTML": "Terms", "attributes": {"href": "/"}}],
	}
	return frappe.get_doc(
		{"doctype": "Builder Component", "component_name": "Edit Test Nav", "block": frappe.as_json(block)}
	).insert()


def make_page(component):
	instance = {
		"blockId": "header",
		"element": "div",
		"extendedFromComponent": component.name,
		"componentVersion": ensure_component_version(component.name),
		"children": [
			{"blockId": "header-link", "isChildOfComponent": component.name, "referenceBlockId": "link"}
		],
	}
	blocks = frappe.as_json([{"blockId": "root", "element": "div", "children": [instance]}])
	return frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": f"Edit Component {frappe.generate_hash(length=6)}",
			"blocks": blocks,
			"draft_blocks": blocks,
		}
	).insert()


def make_ctx(page_id=None):
	queued = []
	return SimpleNamespace(page_id=page_id, queue_client_op=queued.append, queued=queued)


def definition(component_id: str) -> dict:
	return frappe.parse_json(frappe.db.get_value("Builder Component", component_id, "block"))


def instance_on(page_id: str, field: str) -> dict:
	return frappe.parse_json(frappe.db.get_value("Builder Page", page_id, field))[0]["children"][0]


def edit(component, *ops, ctx=None) -> str:
	return run_edit_component(ctx or make_ctx(), {"component_id": component.name, "ops": "\n".join(ops)})


class TestEditComponent(FrappeTestCase):
	def test_edit_reaches_the_definition_and_every_embedding_page(self):
		component = make_component()
		open_page, other_page = make_page(component), make_page(component)
		ctx = make_ctx(open_page.name)

		out = edit(component, '@link "Legal" [href=/terms]', ctx=ctx)

		self.assertIn("synced 2 page(s)", out)
		self.assertEqual(definition(component.name)["children"][0]["innerHTML"], "Legal")
		pinned = resolve_component(component.name, instance_on(other_page.name, "blocks")["componentVersion"])
		link = frappe.parse_json(pinned["block"])["children"][0]
		self.assertEqual((link["innerHTML"], link["attributes"]["href"]), ("Legal", "/terms"))
		self.assertEqual(ctx.queued[0]["tool_name"], "set_page_blocks")

	def test_added_block_is_mirrored_into_embedding_pages(self):
		component = make_component()
		page = make_page(component)

		edit(component, "add @nav", '  a "Blog"')

		new_ref = definition(component.name)["children"][1]["blockId"]
		children = instance_on(page.name, "draft_blocks")["children"]
		self.assertEqual([child["referenceBlockId"] for child in children], ["link", new_ref])

	def test_root_props_declare_and_scripts_land_on_plain_blocks(self):
		component = make_component()

		out = edit(component, "@nav props(theme=dark)", "@link", "  css |", "    a { color: red; }")

		self.assertNotIn("FAILED", out)
		saved = definition(component.name)
		self.assertEqual(saved["props"]["theme"]["value"], "dark")
		self.assertEqual(saved["children"][0]["clientScript"]["css"], "a { color: red; }")

	def test_rejected_edits_change_nothing(self):
		component = make_component()
		wrapper = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "Wraps Nav",
				"block": frappe.as_json(
					{
						"blockId": "wrap",
						"element": "div",
						"children": [
							{"blockId": "inner", "element": "div", "extendedFromComponent": component.name}
						],
					}
				),
			}
		).insert()
		before = definition(component.name)
		for op in (
			f"add @nav\n  div use({wrapper.name})",
			"remove @nav",
			f"add @nav\n  div use({component.name})",
			"generate_page",
		):
			self.assertTrue(edit(component, op).startswith("FAILED"))
		self.assertEqual(definition(component.name), before)

	def test_unknown_component_fails(self):
		out = run_edit_component(make_ctx(), {"component_id": "missing", "ops": "remove @nav"})
		self.assertTrue(out.startswith("FAILED"))
