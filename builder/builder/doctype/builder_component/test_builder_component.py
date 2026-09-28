# Copyright (c) 2023, asdf and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.component_versions import ensure_component_version, resolve_component
from builder.builder.doctype.builder_component.builder_component import get_component_data


def header_block(title: str) -> str:
	return frappe.as_json(
		{
			"blockId": "root",
			"element": "div",
			"children": [{"blockId": "title", "element": "p", "innerHTML": title}],
		}
	)


def make_component(title: str):
	return frappe.get_doc(
		{"doctype": "Builder Component", "component_name": "Sync Header", "block": header_block(title)}
	).insert()


def make_page(component):
	instance = {
		"blockId": "header",
		"element": "div",
		"extendedFromComponent": component.name,
		"componentVersion": ensure_component_version(component.name),
		"children": [
			{"blockId": "header-title", "isChildOfComponent": component.name, "referenceBlockId": "title"}
		],
	}
	blocks = frappe.as_json([{"blockId": "root", "element": "div", "children": [instance]}])
	return frappe.get_doc(
		{"doctype": "Builder Page", "page_title": "Sync Test", "blocks": blocks, "draft_blocks": blocks}
	).insert()


def rendered_title(component_id: str, blocks: str) -> str:
	instance = frappe.parse_json(blocks)[0]["children"][0]
	resolved = resolve_component(component_id, instance["componentVersion"])
	return frappe.parse_json(resolved["block"])["children"][0]["innerHTML"]


class TestBuilderComponent(FrappeTestCase):
	def test_sync_repins_pages_to_the_latest_version(self):
		component = make_component("Old")
		page = make_page(component)
		frappe.db.set_value("Builder Component", component.name, "block", header_block("New"))
		component.reload()

		component.sync_component()

		page.reload()
		self.assertEqual(rendered_title(component.name, page.draft_blocks), "New")
		self.assertEqual(rendered_title(component.name, page.blocks), "New")

	def test_consecutive_saves_are_not_locked(self):
		component = make_component("One")
		component.block = header_block("Two")
		component.save()
		component.block = header_block("Three")
		component.save()
		self.assertEqual(
			frappe.db.get_value("Builder Component", component.name, "block"), header_block("Three")
		)

	def test_render_ignores_a_stale_document_cache(self):
		component = make_component("Saved")
		stale = frappe._dict(block=header_block("Stale"), component_data_script="component.v = 'stale'")
		with (
			patch("frappe.get_cached_value", return_value=stale),
			patch("frappe.get_cached_doc", return_value=stale),
		):
			resolved = resolve_component(component.name)
			data = get_component_data(component.name)
		self.assertEqual(frappe.parse_json(resolved["block"])["children"][0]["innerHTML"], "Saved")
		self.assertEqual(data, {})
