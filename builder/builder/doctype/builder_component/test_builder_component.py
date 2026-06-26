# Copyright (c) 2023, asdf and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.api import get_builder_component_categories
from builder.builder.component_versions import ensure_component_version
from builder.builder.doctype.builder_snapshot.builder_snapshot import get_snapshot_data
from builder.utils import sync_page_templates


class TestBuilderComponent(FrappeTestCase):
	def setUp(self):
		frappe.reload_doc("builder", "doctype", "builder_component", force=True)

	def test_standard_component_fixture_imports_catalog_metadata(self):
		sync_page_templates()

		component = frappe.get_doc("Builder Component", "builder_template_hero_1")

		self.assertEqual(component.component_name, "Hero 1")
		self.assertEqual(component.is_standard, 1)
		self.assertEqual(component.category, "Structure")
		self.assertEqual(component.preview, "/builder_assets/Hero 1/hero_1.png")
		self.assertEqual(component.preview_width, 2)
		self.assertEqual(component.preview_height, 2)
		self.assertEqual(component.sort_order, 4)

	def test_component_version_captures_props_and_scripts(self):
		component_id = f"test_component_{frappe.generate_hash(length=8)}"
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_id": component_id,
				"component_name": "Test Component",
				"block": '{"blockId":"root","children":[]}',
				"component_props": '{"title":{"value":"Hello"}}',
				"component_data_script": "component.title = props.title",
				"component_js": "console.log('component')",
				"component_css": ".component { display: block; }",
			}
		).insert()
		self.addCleanup(frappe.delete_doc, "Builder Component", component.name, force=True)

		version = ensure_component_version(component.name)
		data = get_snapshot_data(version)

		self.assertEqual(data["component_props"], component.component_props)
		self.assertEqual(data["component_data_script"], component.component_data_script)
		self.assertEqual(data["component_js"], component.component_js)
		self.assertEqual(data["component_css"], component.component_css)

	def test_component_categories_are_free_text(self):
		category = f"Test Category {frappe.generate_hash(length=8)}"
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_id": f"test_component_{frappe.generate_hash(length=8)}",
				"component_name": "Test Component Category",
				"category": category,
				"block": '{"blockId":"root","children":[]}',
			}
		).insert()
		self.addCleanup(frappe.delete_doc, "Builder Component", component.name, force=True)

		self.assertIn(category, get_builder_component_categories())

	def test_new_standard_components_export_in_developer_mode(self):
		old_developer_mode = frappe.conf.developer_mode
		frappe.conf.developer_mode = 1
		self.addCleanup(setattr, frappe.conf, "developer_mode", old_developer_mode)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"name": "test_standard_component",
				"component_id": "test_standard_component",
				"is_standard": 1,
			}
		)

		with patch(
			"builder.builder.doctype.builder_component.builder_component.os.path.exists",
			return_value=False,
		), patch(
			"builder.builder.doctype.builder_component.builder_component.export_to_files"
		) as export_to_files:
			component.update_exported_component()

		export_to_files.assert_called_once_with(
			record_list=[["Builder Component", component.name, "builder_component"]],
			record_module="builder",
		)

	def test_new_user_components_do_not_export_in_developer_mode(self):
		old_developer_mode = frappe.conf.developer_mode
		frappe.conf.developer_mode = 1
		self.addCleanup(setattr, frappe.conf, "developer_mode", old_developer_mode)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"name": "test_user_component",
				"component_id": "test_user_component",
				"is_standard": 0,
			}
		)

		with patch(
			"builder.builder.doctype.builder_component.builder_component.os.path.exists",
			return_value=False,
		), patch(
			"builder.builder.doctype.builder_component.builder_component.export_to_files"
		) as export_to_files:
			component.update_exported_component()

		export_to_files.assert_not_called()
