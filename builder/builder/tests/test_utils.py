import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.utils import (
	Block,
	ColonRule,
	camel_case_to_kebab_case,
	clean_data,
	copy_asset_file,
	copy_assets_from_blocks,
	copy_img_to_asset_folder,
	escape_single_quotes,
	execute_script,
	extract_components_from_blocks,
	get_builder_page_preview_file_paths,
	get_template_assets_folder_path,
	is_component_used,
	make_safe_get_request,
	process_block_assets,
	remove_unsafe_fields,
	split_styles,
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

	def test_make_safe_get_request(self):
		# Test with local/private IP addresses (should return None)
		self.assertIsNone(make_safe_get_request("http://127.0.0.1/test"))
		self.assertIsNone(make_safe_get_request("http://localhost/test"))

		# Test with invalid URL
		with self.assertRaises(Exception):
			make_safe_get_request("not-a-url")

	def test_split_styles(self):
		# Test with None
		result = split_styles(None)
		self.assertEqual(result, {"regular": {}, "state": {}})

		# Test with mixed styles
		styles = {"color": "red", "margin": "10px", "hover:color": "blue", "focus:border": "1px solid black"}
		result = split_styles(styles)

		self.assertEqual(result["regular"], {"color": "red", "margin": "10px"})
		self.assertEqual(result["state"], {"hover:color": "blue", "focus:border": "1px solid black"})

	def test_copy_assets_from_blocks(self):
		# Create a temporary directory for testing
		import tempfile

		with tempfile.TemporaryDirectory() as temp_dir:
			# Test with single block
			block = Block(element="img", attributes={"src": "/files/test.jpg"})
			copy_assets_from_blocks(block, temp_dir)

			# Test with list of blocks
			blocks = [
				{
					"element": "div",
					"children": [{"element": "img", "attributes": {"src": "/files/test2.jpg"}}],
				},
				{"element": "video", "attributes": {"src": "/files/test.mp4"}},
			]
			copy_assets_from_blocks(blocks, temp_dir)

	def test_process_block_assets(self):
		import tempfile

		with tempfile.TemporaryDirectory() as temp_dir:
			# Test with img element
			block = {"element": "img", "attributes": {"src": "/files/test.jpg"}}
			process_block_assets(block, temp_dir)

			# Test with video element
			block = {"element": "video", "attributes": {"src": "/files/test.mp4"}}
			process_block_assets(block, temp_dir)

			# Test with non-media element
			block = {"element": "div", "attributes": {"class": "test"}}
			process_block_assets(block, temp_dir)

	def test_copy_asset_file(self):
		import tempfile

		with tempfile.TemporaryDirectory() as temp_dir:
			# Test with None/invalid inputs
			result = copy_asset_file(None, temp_dir)
			self.assertIsNone(result)

			result = copy_asset_file("", temp_dir)
			self.assertIsNone(result)

			result = copy_asset_file(123, temp_dir)
			self.assertIsNone(result)

			# Test with non-existent file URLs
			result = copy_asset_file("/files/nonexistent.jpg", temp_dir)
			self.assertIsNone(result)

			result = copy_asset_file("/builder_assets/nonexistent.jpg", temp_dir)
			self.assertIsNone(result)

	def test_extract_components_from_blocks(self):
		# Test with blocks containing components
		blocks = [
			{
				"element": "div",
				"extendedFromComponent": "TestComponent1",
				"children": [{"element": "span", "extendedFromComponent": "TestComponent2"}],
			},
			{
				"element": "section",
				"children": [{"element": "div", "extendedFromComponent": "TestComponent1"}],
			},
		]

		# Mock frappe.get_cached_doc using unittest.mock

		with patch("frappe.get_cached_doc") as mock_get_cached_doc:
			mock_get_cached_doc.return_value = frappe._dict(block='{"element": "div"}')

			components = extract_components_from_blocks(blocks)
			self.assertIn("TestComponent1", components)
			self.assertIn("TestComponent2", components)

		# Test with single block (not a list)
		single_block = {"element": "div", "extendedFromComponent": "SingleComponent"}

		with patch("frappe.get_cached_doc") as mock_get_cached_doc:
			mock_get_cached_doc.return_value = frappe._dict(block='{"element": "div"}')

			components = extract_components_from_blocks(single_block)
			self.assertIn("SingleComponent", components)

	def test_copy_img_to_asset_folder(self):
		test_page = frappe._dict(name="test-page")

		# Test with non-img elements (should be ignored)
		block = Block()
		block.element = "div"
		block.children = []
		copy_img_to_asset_folder(block, test_page)  # Should not raise error

		# Test with img element but no attributes
		block = Block()
		block.element = "img"
		block.attributes = None
		block.children = []
		copy_img_to_asset_folder(block, test_page)  # Should not raise error

		# Test with img element but no src attribute
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict()
		block.children = []
		copy_img_to_asset_folder(block, test_page)  # Should not raise error

		# Test with img element and external src (should be ignored)
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="https://example.com/image.jpg")
		block.children = []
		original_src = block.attributes.src
		copy_img_to_asset_folder(block, test_page)
		self.assertEqual(block.attributes.src, original_src)  # Should remain unchanged

		# Test with img element and builder_assets src (should be ignored)
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="/builder_assets/local-image.jpg")
		block.children = []
		original_src = block.attributes.src
		copy_img_to_asset_folder(block, test_page)
		self.assertEqual(block.attributes.src, original_src)  # Should remain unchanged

		# Test with nested blocks containing img elements
		child_block = Block()
		child_block.element = "img"
		child_block.attributes = frappe._dict(src="https://example.com/nested.jpg")
		child_block.children = []

		parent_block = Block()
		parent_block.element = "div"
		parent_block.attributes = frappe._dict()
		parent_block.children = [child_block]

		copy_img_to_asset_folder(parent_block, test_page)  # Should process children recursively

		# Test with local file src that doesn't exist in database
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="/files/nonexistent-image.jpg")
		block.children = []

		with patch("frappe.get_all") as mock_get_all:
			mock_get_all.return_value = []  # No files found
			original_src = block.attributes.src
			copy_img_to_asset_folder(block, test_page)
			# Should update src even if file not found
			self.assertEqual(block.attributes.src, f"/builder_assets/{test_page.name}/nonexistent-image.jpg")

		# Test with valid local file that exists in database
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="/files/test-image.jpg")
		block.children = []

		mock_file = frappe._dict()
		mock_file.get_full_path = lambda: "/fake/path/test-image.jpg"

		with (
			patch("frappe.get_all") as mock_get_all,
			patch("frappe.get_doc") as mock_get_doc,
			patch("shutil.copy") as mock_copy,
			patch("builder.utils.get_template_assets_folder_path") as mock_get_path,
		):
			mock_get_all.return_value = [frappe._dict(name="file-123")]
			mock_get_doc.return_value = mock_file
			mock_get_path.return_value = "/fake/assets/path"

			copy_img_to_asset_folder(block, test_page)

			# Verify file operations were called correctly
			mock_get_all.assert_called_once_with(
				"File", filters={"file_url": "/files/test-image.jpg"}, fields=["name"]
			)
			mock_get_doc.assert_called_once_with("File", "file-123")
			mock_copy.assert_called_once_with("/fake/path/test-image.jpg", "/fake/assets/path")

			# Verify src was updated correctly
			self.assertEqual(block.attributes.src, f"/builder_assets/{test_page.name}/test-image.jpg")

		# Test with site URL prefix in src
		site_url = frappe.utils.get_url()
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src=f"{site_url}/files/prefixed-image.jpg")
		block.children = []

		with patch("frappe.get_all") as mock_get_all:
			mock_get_all.return_value = []
			copy_img_to_asset_folder(block, test_page)
			# Should strip site URL and update path
			self.assertEqual(block.attributes.src, f"/builder_assets/{test_page.name}/prefixed-image.jpg")

		# Test with URL-encoded filename
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="/files/image%20with%20spaces.jpg")
		block.children = []

		with patch("frappe.get_all") as mock_get_all:
			# Should decode URL and search for decoded filename
			mock_get_all.return_value = []
			copy_img_to_asset_folder(block, test_page)
			mock_get_all.assert_called_with(
				"File", filters={"file_url": "/files/image with spaces.jpg"}, fields=["name"]
			)
			self.assertEqual(block.attributes.src, f"/builder_assets/{test_page.name}/image with spaces.jpg")

		# Test error handling when file copy fails
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="/files/error-test.jpg")
		block.children = []

		mock_file = frappe._dict()
		mock_file.get_full_path = lambda: "/fake/path/error-test.jpg"

		with (
			patch("frappe.get_all") as mock_get_all,
			patch("frappe.get_doc") as mock_get_doc,
			patch("shutil.copy") as mock_copy,
			patch("builder.utils.get_template_assets_folder_path") as mock_get_path,
		):
			mock_get_all.return_value = [frappe._dict(name="file-456")]
			mock_get_doc.return_value = mock_file
			mock_get_path.return_value = "/fake/assets/path"
			mock_copy.side_effect = OSError("Permission denied")

			# Function should raise exception when copy fails
			with self.assertRaises(OSError):
				copy_img_to_asset_folder(block, test_page)

		# Test with empty/None src attribute
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="")
		block.children = []
		copy_img_to_asset_folder(block, test_page)  # Should not process empty src

		block.attributes = frappe._dict(src=None)
		copy_img_to_asset_folder(block, test_page)  # Should not process None src

		# Test with malformed URLs
		block = Block()
		block.element = "img"
		block.attributes = frappe._dict(src="/uploads/image.jpg")  # Not a /files path
		block.children = []
		original_src = block.attributes.src
		copy_img_to_asset_folder(block, test_page)
		self.assertEqual(block.attributes.src, original_src)  # Should remain unchanged

		# Test deeply nested structure
		grandchild = Block()
		grandchild.element = "img"
		grandchild.attributes = frappe._dict(src="/files/deep-nested.jpg")
		grandchild.children = []

		child = Block()
		child.element = "span"
		child.attributes = frappe._dict()
		child.children = [grandchild]

		parent = Block()
		parent.element = "div"
		parent.attributes = frappe._dict()
		parent.children = [child]

		with patch("frappe.get_all") as mock_get_all:
			mock_get_all.return_value = []
			copy_img_to_asset_folder(parent, test_page)
			# Should process grandchild img element
			self.assertEqual(grandchild.attributes.src, f"/builder_assets/{test_page.name}/deep-nested.jpg")

		# Test with block that has None children
		block = Block()
		block.element = "div"
		block.attributes = frappe._dict()
		block.children = None
		copy_img_to_asset_folder(block, test_page)  # Should handle None children gracefully
