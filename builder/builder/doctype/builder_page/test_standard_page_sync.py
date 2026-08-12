# Copyright (c) 2023, asdf and Contributors
# See license.txt

import contextlib
import os
import shutil
import tempfile
import unittest.mock as mock

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.utils import Block


class TestStandardPageSync(FrappeTestCase):
	"""Verify that builder_files on disk stay in sync with DB operations.

	Filesystem calls are mocked, so these test which files the sync decides to
	write or delete, not the shutil behaviour underneath.
	"""

	# builder is always installed, so frappe.get_app_path succeeds
	FIXTURE_APP = "builder"
	EXPORT_MODULE = "builder.export_import_standard_page"
	# export_page_as_standard is imported into builder_page, so patch it there
	PAGE_MODULE = "builder.builder.doctype.builder_page.builder_page"

	# ------------------------------------------------------------------ helpers

	@staticmethod
	def without_developer_mode():
		"""Context manager that temporarily disables developer_mode."""

		@contextlib.contextmanager
		def cm():
			original = frappe.conf.developer_mode
			frappe.conf.developer_mode = 0
			try:
				yield
			finally:
				frappe.conf.developer_mode = original

		return cm()

	@contextlib.contextmanager
	def with_developer_mode(self):
		frappe.conf.developer_mode = 1
		try:
			yield
		finally:
			frappe.conf.developer_mode = 0

	@contextlib.contextmanager
	def mock_page_sync_deletes(self, resource_delete_patch: str | None = None):
		"""Mock filesystem delete handlers during page cleanup; yield the resource mock if given."""
		with contextlib.ExitStack() as stack:
			stack.enter_context(mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files"))
			resource_mock = None
			if resource_delete_patch:
				resource_mock = stack.enter_context(mock.patch(resource_delete_patch))
			yield resource_mock

	def delete_if_exists(self, doctype: str, name: str, **kwargs):
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, ignore_permissions=True, **kwargs)

	def delete_renamed_if_exists(self, doctype: str, old_name: str, new_name: str, **kwargs):
		actual_name = new_name if frappe.db.exists(doctype, new_name) else old_name
		self.delete_if_exists(doctype, actual_name, **kwargs)

	def assert_page_files_delete_called_once(self, mock_delete):
		mock_delete.assert_called_once()
		self.assertEqual(mock_delete.call_args[0][1], self.FIXTURE_APP)

	def assert_sync_delete_called_once(self, mock_delete, resource_name: str):
		mock_delete.assert_called_once()
		args = mock_delete.call_args[0]
		self.assertEqual(args[0], resource_name)
		self.assertEqual(args[1], self.FIXTURE_APP)

	def assert_builder_files_deleted(self, mock_delete, name: str, subdir: str):
		"""The record sweeps every installed app, so assert it reached the fixture app."""
		mock_delete.assert_called()
		calls = [call[0] for call in mock_delete.call_args_list]
		self.assertIn((name, self.FIXTURE_APP, subdir), calls)

	def assert_export_contains(self, mock_export, item):
		mock_export.assert_called()
		self.assertIn(item, mock_export.call_args[0][0])

	def uncheck_standard(self, page):
		page.is_standard = 0
		page.app = ""
		page.save(ignore_permissions=True)

	def make_component(self):
		with self.without_developer_mode():
			component_root = Block(element="div", blockId="comp-block-1")
			component = frappe.get_doc(
				{
					"doctype": "Builder Component",
					"block": component_root.as_json(),
				}
			)
			# on_update queues clear_page_cache; avoid document lock in tests.
			with mock.patch.object(type(component), "queue_action"):
				component.insert(ignore_permissions=True)
			return component

	def make_font(self):
		with self.without_developer_mode():
			return frappe.get_doc(
				{
					"doctype": "User Font",
					"font_name": f"Test Font {frappe.generate_hash(4)}",
				}
			).insert(ignore_permissions=True)

	def blocks_with_font(self, font):
		page_block = Block(element="div", baseStyles={"fontFamily": font.font_name})
		return frappe.as_json([page_block.as_dict()])

	def make_variable(self, variable_name: str | None = None):
		variable_name = variable_name or f"test-var-{frappe.generate_hash(4)}"
		with self.without_developer_mode():
			return frappe.get_doc(
				{
					"doctype": "Builder Token",
					"token_name": variable_name,
					"type": "Color",
					"value": "#ff0000",
				}
			).insert(ignore_permissions=True)

	def blocks_with_component(self, component):
		page_block = Block(extendedFromComponent=component.name)
		return frappe.as_json([page_block.as_dict()])

	def blocks_with_variable(self, variable):
		page_block = Block(element="div", baseStyles={"color": f"var(--{variable.name})"})
		return frappe.as_json([page_block.as_dict()])

	def blocks_with_unrecorded_dependencies(self):
		"""Blocks naming a bundled font and a plain CSS variable, neither of which has a record."""
		page_block = Block(
			element="div",
			baseStyles={"fontFamily": "Bundled Sans", "color": "var(--tw-ring-color)"},
		)
		return frappe.as_json([page_block.as_dict()])

	def make_secondary_standard_page(self, page_title: str, blocks: str = "[]", script=None):
		"""Create another standard page without triggering export side effects."""
		with self.without_developer_mode():
			page = frappe.get_doc(
				{
					"doctype": "Builder Page",
					"page_title": page_title,
					"route": f"/test-standard-{frappe.generate_hash(4)}",
					"blocks": blocks,
					"is_standard": 1,
					"app": self.FIXTURE_APP,
				}
			).insert(ignore_permissions=True)
			if script:
				page.append("client_scripts", {"builder_script": script.name})
				page.save(ignore_permissions=True)
			return page

	def make_page(
		self,
		page_name: str,
		with_script: bool = False,
		with_component=None,
		with_variable=None,
	):
		with self.without_developer_mode():
			blocks = "[]"
			if with_component:
				blocks = self.blocks_with_component(with_component)
			elif with_variable:
				blocks = self.blocks_with_variable(with_variable)

			doc = frappe.get_doc(
				{
					"doctype": "Builder Page",
					"page_title": page_name,
					"route": f"/test-standard-{frappe.generate_hash(4)}",
					"blocks": blocks,
					"is_standard": 1,
					"app": self.FIXTURE_APP,
				}
			).insert(ignore_permissions=True)
			if with_script:
				script = frappe.get_doc(
					{
						"doctype": "Builder Client Script",
						"script_type": "JavaScript",
						"script": "// test",
					}
				).insert(ignore_permissions=True)
				doc.append("client_scripts", {"builder_script": script.name})
				doc.save(ignore_permissions=True)
				doc.reload()
				return doc, script
		return doc

	# ------------------------------------------------------------------ tests

	def test_export_page_without_data_script(self):
		"""A page with no data script exports an empty data_script.py."""
		from builder.export_import_standard_page import export_page_as_standard

		page = self.make_secondary_standard_page("export-without-data-script")
		export_root = tempfile.mkdtemp()
		try:
			with mock.patch.object(frappe, "get_app_path", return_value=export_root):
				export_page_as_standard(page.name, target_app=self.FIXTURE_APP)

			data_script_path = os.path.join(
				export_root, "builder_files", "pages", frappe.scrub(page.page_name), "data_script.py"
			)
			self.assertTrue(os.path.isfile(data_script_path))
			with open(data_script_path) as f:
				self.assertEqual(f.read(), "")
		finally:
			shutil.rmtree(export_root, ignore_errors=True)
			self.delete_if_exists("Builder Page", page.name, force=True)

	def test_export_client_script_without_body(self):
		"""A script with no body exports, and a CSS script lands in a .css file."""
		from builder.utils import export_client_scripts

		# script is mandatory, so only a fixture import or ignore_mandatory gets here
		script = frappe.get_doc(
			{"doctype": "Builder Client Script", "script_type": "CSS", "script": None}
		).insert(ignore_permissions=True, ignore_mandatory=True)
		export_root = tempfile.mkdtemp()
		try:
			export_client_scripts([script.name], export_root)

			script_dir = os.path.join(export_root, frappe.scrub(script.name))
			with open(os.path.join(script_dir, "client_script.css")) as f:
				self.assertEqual(f.read(), "")
			self.assertFalse(os.path.exists(os.path.join(script_dir, "client_script.js")))
		finally:
			shutil.rmtree(export_root, ignore_errors=True)
			self.delete_if_exists("Builder Client Script", script.name, force=1)

	def test_on_trash_page_with_unrecorded_dependencies(self):
		"""A bundled font or plain CSS variable must not block deletion of a standard page."""
		page = self.make_secondary_standard_page(
			"trash-unrecorded-deps", blocks=self.blocks_with_unrecorded_dependencies()
		)
		with self.mock_page_sync_deletes(f"{self.EXPORT_MODULE}.delete_standard_font_files") as mock_del_font:
			with self.with_developer_mode():
				page.delete(ignore_permissions=True)
			mock_del_font.assert_not_called()
		self.assertFalse(frappe.db.exists("Builder Page", page.name))

	def test_on_trash_standard_page_removes_directory(self):
		page = self.make_page("trash-sync-page")
		with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files") as mock_delete:
			with self.with_developer_mode():
				page.delete(ignore_permissions=True)
			self.assert_page_files_delete_called_once(mock_delete)

	def test_on_trash_standard_page_removes_orphaned_script(self):
		page, script = self.make_page("trash-sync-page-script", with_script=True)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self.with_developer_mode():
					page.delete(ignore_permissions=True)
				self.assert_sync_delete_called_once(mock_del_script, script.name)
		finally:
			self.delete_if_exists("Builder Client Script", script.name)

	def test_on_trash_shared_script_is_not_removed(self):
		page1, script = self.make_page("trash-shared-page-1", with_script=True)
		page2 = self.make_secondary_standard_page("trash-shared-page-2", script=script)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self.with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_script.assert_not_called()
		finally:
			self.delete_if_exists("Builder Page", page2.name)
			self.delete_if_exists("Builder Client Script", script.name)

	def test_after_rename_standard_page_reexports(self):
		"""A rename drops the old export and writes a new one, so the JSON holds the new name."""
		page = self.make_page("rename-sync-page-old")
		new_name = f"rename-sync-page-new-{frappe.generate_hash(4)}"
		try:
			with (
				mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files") as mock_delete,
				mock.patch(f"{self.PAGE_MODULE}.export_page_as_standard") as mock_export,
			):
				with self.with_developer_mode():
					frappe.rename_doc("Builder Page", page.name, new_name, force=True)
				self.assert_sync_delete_called_once(mock_delete, page.name)
				mock_export.assert_called_once_with(new_name, target_app=self.FIXTURE_APP)
		finally:
			self.delete_if_exists("Builder Page", new_name)
			self.delete_if_exists("Builder Page", page.name)

	def test_uninstalled_app_does_not_block_delete(self):
		"""app is plain Data, so it can name an app that is gone. Deleting must still work."""
		page = self.make_secondary_standard_page("uninstalled-app-page")
		frappe.db.set_value("Builder Page", page.name, "app", "no_such_app", update_modified=False)
		page.reload()
		with self.with_developer_mode():
			page.delete(ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Builder Page", page.name))

	def test_migrate_does_not_rewrite_exported_files(self):
		"""Importing a standard page during migrate must not write back to the app source."""
		page = self.make_page("migrate-noexport-page")
		try:
			with mock.patch(f"{self.PAGE_MODULE}.export_page_as_standard") as mock_export:
				with self.with_developer_mode():
					frappe.flags.in_migrate = True
					try:
						page.save(ignore_permissions=True)
					finally:
						frappe.flags.in_migrate = False
				mock_export.assert_not_called()
		finally:
			self.delete_if_exists("Builder Page", page.name, force=True)

	def test_change_app_removes_export_from_old_app(self):
		page = self.make_page("app-change-page")
		try:
			with (
				mock.patch(f"{self.PAGE_MODULE}.export_page_as_standard"),
				mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files") as mock_delete,
			):
				with self.with_developer_mode():
					page.app = "frappe"
					page.save(ignore_permissions=True)
				self.assert_sync_delete_called_once(mock_delete, page.page_name)
		finally:
			self.delete_if_exists("Builder Page", page.name, force=True)

	def test_uncheck_standard_page_removes_files(self):
		page = self.make_page("uncheck-std-page")
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files") as mock_delete:
				with self.with_developer_mode():
					self.uncheck_standard(page)
				self.assert_page_files_delete_called_once(mock_delete)
		finally:
			self.delete_if_exists("Builder Page", page.name, force=True)

	def test_uncheck_standard_page_removes_orphaned_scripts(self):
		page, script = self.make_page("uncheck-std-scripts", with_script=True)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self.with_developer_mode():
					self.uncheck_standard(page)
				self.assert_sync_delete_called_once(mock_del_script, script.name)
		finally:
			self.delete_if_exists("Builder Page", page.name, force=True)
			self.delete_if_exists("Builder Client Script", script.name)

	def test_client_script_on_trash_removes_directory(self):
		page, script = self.make_page("cs-trash-page", with_script=True)
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_builder_files") as mock_del:
				with self.with_developer_mode():
					script_name = script.name
					frappe.delete_doc("Builder Client Script", script_name, force=1)
				self.assert_builder_files_deleted(mock_del, script_name, "client_scripts")
		finally:
			self.delete_if_exists("Builder Page", page.name)

	def test_client_script_after_rename_reexports(self):
		"""A rename drops the old export and writes a new one, so the JSON holds the new name."""
		page, script = self.make_page("cs-rename-page", with_script=True)
		old_script_name = script.name
		new_script_name = f"renamed-{frappe.generate_hash(4)}"
		try:
			with (
				mock.patch(f"{self.EXPORT_MODULE}.delete_standard_builder_files") as mock_delete,
				mock.patch(f"{self.EXPORT_MODULE}.export_client_scripts") as mock_export,
			):
				with self.with_developer_mode():
					frappe.rename_doc("Builder Client Script", old_script_name, new_script_name, force=True)
				self.assert_builder_files_deleted(mock_delete, old_script_name, "client_scripts")
				self.assert_export_contains(mock_export, new_script_name)
		finally:
			self.delete_renamed_if_exists("Builder Client Script", old_script_name, new_script_name, force=1)
			self.delete_if_exists("Builder Page", page.name)

	# -------------------------------------------------------- component tests

	def test_component_on_trash_removes_exported_files(self):
		component = self.make_component()
		with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_builder_files") as mock_delete:
			with self.with_developer_mode():
				frappe.delete_doc("Builder Component", component.name, force=1)
			self.assert_builder_files_deleted(mock_delete, component.name, "components")

	def test_component_after_rename_removes_old_exported_files(self):
		component = self.make_component()
		old_name = component.name
		new_name = f"renamed-comp-{frappe.generate_hash(4)}"
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_builder_files") as mock_delete:
				with self.with_developer_mode():
					frappe.rename_doc("Builder Component", old_name, new_name, force=True)
				self.assert_builder_files_deleted(mock_delete, old_name, "components")
		finally:
			self.delete_renamed_if_exists("Builder Component", old_name, new_name, force=1)

	def test_component_on_update_exports_to_referencing_standard_pages(self):
		component = self.make_component()
		page = self.make_page("comp-update-page", with_component=component)
		try:
			with (
				mock.patch(f"{self.EXPORT_MODULE}.export_components") as mock_export,
				mock.patch.object(type(component), "queue_action"),
			):
				with self.with_developer_mode():
					component.block = Block(element="section", blockId="comp-block-2").as_json()
					component.save(ignore_permissions=True)
				self.assert_export_contains(mock_export, component.component_id)
		finally:
			self.delete_if_exists("Builder Page", page.name)
			self.delete_if_exists("Builder Component", component.name, force=1)

	def test_on_trash_standard_page_removes_orphaned_component(self):
		component = self.make_component()
		page = self.make_page("trash-sync-page-component", with_component=component)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_component_files"
			) as mock_del_component:
				with self.with_developer_mode():
					page.delete(ignore_permissions=True)
				self.assert_sync_delete_called_once(mock_del_component, component.name)
		finally:
			self.delete_if_exists("Builder Component", component.name, force=1)

	def test_on_trash_shared_component_is_not_removed(self):
		component = self.make_component()
		page1 = self.make_page("trash-shared-comp-page-1", with_component=component)
		page2 = self.make_secondary_standard_page(
			"trash-shared-comp-page-2",
			blocks=self.blocks_with_component(component),
		)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_component_files"
			) as mock_del_component:
				with self.with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_component.assert_not_called()
		finally:
			self.delete_if_exists("Builder Page", page2.name)
			self.delete_if_exists("Builder Component", component.name, force=1)

	# --------------------------------------------------------- variable tests

	def test_variable_on_trash_removes_exported_files(self):
		variable = self.make_variable()
		with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_builder_files") as mock_delete:
			with self.with_developer_mode():
				frappe.delete_doc("Builder Token", variable.name, force=1)
			self.assert_builder_files_deleted(mock_delete, variable.name, "variables")

	def test_variable_after_rename_removes_old_exported_files(self):
		variable = self.make_variable()
		old_name = variable.name
		new_name = f"renamed-var-{frappe.generate_hash(4)}"
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_builder_files") as mock_delete:
				with self.with_developer_mode():
					frappe.rename_doc("Builder Token", old_name, new_name, force=True)
				self.assert_builder_files_deleted(mock_delete, old_name, "variables")
		finally:
			self.delete_renamed_if_exists("Builder Token", old_name, new_name, force=1)

	def test_variable_on_update_exports_to_referencing_standard_pages(self):
		variable = self.make_variable()
		page = self.make_page("var-update-page", with_variable=variable)
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.export_variables") as mock_export:
				with self.with_developer_mode():
					variable.value = "#00ff00"
					variable.save(ignore_permissions=True)
				self.assert_export_contains(mock_export, variable.name)
		finally:
			self.delete_if_exists("Builder Page", page.name)
			self.delete_if_exists("Builder Token", variable.name, force=1)

	def test_variable_uncheck_is_standard_removes_module_export(self):
		variable = self.make_variable()
		variable.is_standard = 1
		variable.save(ignore_permissions=True)
		try:
			with mock.patch(
				"builder.builder.doctype.builder_token.builder_token.delete_folder"
			) as mock_delete_folder:
				with self.with_developer_mode():
					variable.is_standard = 0
					variable.save(ignore_permissions=True)
				mock_delete_folder.assert_called_once_with("builder", "builder_token", variable.name)
		finally:
			self.delete_if_exists("Builder Token", variable.name, force=1)

	def test_on_trash_standard_page_removes_orphaned_variable(self):
		variable = self.make_variable()
		page = self.make_page("trash-sync-page-variable", with_variable=variable)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_variable_files"
			) as mock_del_variable:
				with self.with_developer_mode():
					page.delete(ignore_permissions=True)
				self.assert_sync_delete_called_once(mock_del_variable, variable.name)
		finally:
			self.delete_if_exists("Builder Token", variable.name, force=1)

	def test_on_trash_shared_variable_is_not_removed(self):
		variable = self.make_variable()
		page1 = self.make_page("trash-shared-var-page-1", with_variable=variable)
		page2 = self.make_secondary_standard_page(
			"trash-shared-var-page-2",
			blocks=self.blocks_with_variable(variable),
		)
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_variable_files"
			) as mock_del_variable:
				with self.with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_variable.assert_not_called()
		finally:
			self.delete_if_exists("Builder Page", page2.name)
			self.delete_if_exists("Builder Token", variable.name, force=1)

	# ------------------------------------------------------------- font tests

	def test_on_trash_standard_page_removes_orphaned_font(self):
		font = self.make_font()
		page = self.make_secondary_standard_page("trash-font-page", blocks=self.blocks_with_font(font))
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_font_files"
			) as mock_del_font:
				with self.with_developer_mode():
					page.delete(ignore_permissions=True)
				self.assert_sync_delete_called_once(mock_del_font, font.font_name)
		finally:
			self.delete_if_exists("User Font", font.name, force=1)

	def test_on_trash_shared_font_is_not_removed(self):
		font = self.make_font()
		page1 = self.make_secondary_standard_page("trash-shared-font-1", blocks=self.blocks_with_font(font))
		page2 = self.make_secondary_standard_page("trash-shared-font-2", blocks=self.blocks_with_font(font))
		try:
			with self.mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_font_files"
			) as mock_del_font:
				with self.with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_font.assert_not_called()
		finally:
			self.delete_if_exists("Builder Page", page2.name)
			self.delete_if_exists("User Font", font.name, force=1)

	# -------------------------------------------------- client script tests

	def test_client_script_on_update_exports_to_referencing_standard_pages(self):
		page, script = self.make_page("cs-update-page", with_script=True)
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.export_client_scripts") as mock_export:
				with self.with_developer_mode():
					script.script = "// updated test"
					script.save(ignore_permissions=True)
				self.assert_export_contains(mock_export, script.name)
		finally:
			self.delete_if_exists("Builder Page", page.name)
			self.delete_if_exists("Builder Client Script", script.name)
