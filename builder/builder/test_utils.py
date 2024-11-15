from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.utils import (
	camel_case_to_kebab_case,
	escape_single_quotes,
	execute_script,
	get_builder_page_preview_file_paths,
	get_dummy_blocks,
	get_template_assets_folder_path,
	is_component_used,
	remove_unsafe_fields,
)


class TestBuilderPage(FrappeTestCase):
	def test_camel_case_to_kebab_case(self):
		self.assertEqual(camel_case_to_kebab_case("backgroundColor"), "background-color")
		self.assertEqual(camel_case_to_kebab_case("Color"), "color")
		self.assertEqual(camel_case_to_kebab_case("color"), "color")
		self.assertEqual(camel_case_to_kebab_case("NewPage"), "new-page")
		self.assertEqual(camel_case_to_kebab_case("new page", remove_spaces=True), "newpage")

	def test_escape_single_quotes(self):
		self.assertEqual(escape_single_quotes("Hello 'World'"), "Hello \\'World\\'")
		self.assertEqual(escape_single_quotes("Hello World"), "Hello World")

	def test_is_component_used(self):
		dummy_blocks = get_dummy_blocks()
		self.assertTrue(is_component_used(dummy_blocks, "component-1"))
		self.assertTrue(is_component_used(dummy_blocks, "component-2"))
		self.assertFalse(is_component_used(dummy_blocks, "component-3"))

	def test_get_builder_page_preview_file_paths(self):
		page_doc = frappe._dict(
			{
				"name": "test-page",
				"is_template": False,
			}
		)
		public_path, local_path = get_builder_page_preview_file_paths(page_doc)
		self.assertRegex(public_path, r"/files/test-page-preview.webp\?v=\w{5}")
		self.assertEqual(local_path, f"{frappe.local.site_path}/public/files/test-page-preview.webp")

		page_doc.is_template = True
		public_path, local_path = get_builder_page_preview_file_paths(page_doc)
		self.assertEqual(public_path, "/builder_assets/test-page/preview.webp")
		self.assertEqual(
			local_path, f"{frappe.get_app_path('builder')}/www/builder_assets/test-page/preview.webp"
		)

	def test_get_template_assets_folder_path(self):
		page_doc = frappe._dict({"name": "mypage"})
		path = get_template_assets_folder_path(page_doc)
		self.assertEqual(path, f"{frappe.get_app_path('builder')}/www/builder_assets/mypage")

	@patch("builder.utils.is_safe_exec_enabled", return_value=False)
	@patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=False)
	def test_execute_script_with_enabled_server_script(self, *args):
		script = "data.test = frappe.get_doc('User', 'Administrator').email"
		_locals = dict(data=frappe._dict())
		execute_script(script, _locals, "test.py")
		self.assertEqual(_locals["data"]["test"], "admin@example.com")

	@patch("builder.utils.is_safe_exec_enabled", return_value=True)
	@patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True)
	def test_execute_script_with_disabled_server_script(self, *args):
		script = "data.test = frappe.get_doc('User', 'Administrator').email"
		_locals = dict(data=frappe._dict())
		execute_script(script, _locals, "test.py")
		self.assertEqual(_locals["data"]["test"], "admin@example.com")

		script = "data.users = frappe.db.get_all('User')"
		execute_script(script, _locals, "test.py")
		self.assertTrue(_locals["data"]["users"])

		script = "data.users = frappe.db.get_all('User')"
		execute_script(script, _locals, "test.py")
		self.assertTrue(_locals["data"]["users"])
