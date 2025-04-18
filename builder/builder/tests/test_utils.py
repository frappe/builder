import os

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.utils import (
	ColonRule,
	camel_case_to_kebab_case,
	clean_data,
	escape_single_quotes,
	execute_script,
	get_builder_page_preview_file_paths,
	get_template_assets_folder_path,
	is_component_used,
	remove_unsafe_fields,
)


class TestBuilderUtils(FrappeTestCase):
	def test_camel_case_to_kebab_case(self):
		test_cases = {
			"backgroundColor": "background-color",
			"marginTop": "margin-top",
			"WebsiteHeader": "website-header",
			"simple": "simple",
		}

		for input_str, expected in test_cases.items():
			self.assertEqual(camel_case_to_kebab_case(input_str), expected)

	def test_escape_single_quotes(self):
		test_cases = {
			"It's working": "It\\'s working",
			"Don't do this": "Don\\'t do this",
			"Regular text": "Regular text",
			"'Quoted'": "\\'Quoted\\'",
		}

		for input_str, expected in test_cases.items():
			self.assertEqual(escape_single_quotes(input_str), expected)

	def test_preview_file_paths(self):
		test_page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Preview Test", "route": "/preview-test", "block": "[]"}
		).insert(ignore_if_duplicate=True)

		public_path, local_path = get_builder_page_preview_file_paths(test_page)

		self.assertTrue(public_path.startswith("/files/"))
		self.assertTrue(local_path.endswith(".webp"))
		self.assertTrue(test_page.name in public_path)

		self.assertTrue(local_path.endswith(".webp"))
		self.assertTrue("/public/files/" in local_path)

		test_page.delete()

	def test_get_template_assets_folder_path(self):
		test_page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Template Test",
				"route": "/template-test",
				"is_template": True,
			}
		).insert(ignore_if_duplicate=True)

		folder_path = get_template_assets_folder_path(test_page)
		self.assertTrue(folder_path.endswith(f"builder_assets/{test_page.name}"))
		self.assertTrue(os.path.exists(folder_path))

		test_page.delete()

	def test_get_builder_page_preview_file_paths_for_template(self):
		test_page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Template Preview Test",
				"route": "/template-preview-test",
				"is_template": True,
			}
		).insert(ignore_if_duplicate=True)

		public_path, local_path = get_builder_page_preview_file_paths(test_page)

		self.assertTrue(public_path.startswith("/builder_assets/"))
		self.assertTrue(public_path.endswith("preview.webp"))
		self.assertTrue(test_page.name in public_path)

		self.assertTrue(local_path.endswith("preview.webp"))
		self.assertTrue("/builder_assets/" in local_path)

		test_page.delete()

	def test_remove_unsafe_fields(self):
		dummy_fields = ["safe_field", "count(unsafe)", "custom_field as new_field"]
		safe_fields = remove_unsafe_fields(dummy_fields)
		self.assertIn("safe_field", safe_fields)
		self.assertNotIn("count(unsafe)", safe_fields)
		self.assertIn("custom_field as new_field", safe_fields)

	def test_is_component_used(self):
		test_page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Test",
				"route": "/component-test",
				"block": '[{"extendedFromComponent":"TestComponent"}]',
			}
		).insert(ignore_if_duplicate=True)

		self.assertTrue(is_component_used(test_page.block, "TestComponent"))
		self.assertFalse(is_component_used(test_page.block, "NonExistentComponent"))

		test_page.delete()

	def test_execute_script(self):
		with self.assertRaises(Exception):
			execute_script("a + b + c", {"a": 2, "b": 2}, "test.py")
		data = frappe._dict({})
		execute_script("data.sum = a + b", {"data": data, "a": 2, "b": 2}, "test.py")
		self.assertEqual(data.sum, 4)

	def test_colon_rule(self):
		rule = ColonRule("/test/<name>", endpoint="test_endpoint")
		self.assertEqual(rule.rule, "/test/<name>")
		self.assertEqual(rule.endpoint, "test_endpoint")

		rule2 = ColonRule("/test/:name", endpoint="test_endpoint")
		self.assertEqual(rule2.rule, "/test/<name>")
		self.assertEqual(rule2.endpoint, "test_endpoint")

		rule3 = ColonRule("/test/:name/:id", endpoint="test_endpoint")
		self.assertEqual(rule3.rule, "/test/<name>/<id>")
		self.assertEqual(rule3.endpoint, "test_endpoint")

	def test_clean_data(self):
		data = {
			"test": "value",
			"test2": "value2",
			"test3": lambda x: x,
			"test4": None,
			"test5": frappe._dict(),
			"test6": {}.items,
		}
		cleaned_data = clean_data(data)
		self.assertEqual(cleaned_data, {"test": "value", "test2": "value2", "test4": None, "test5": {}})
