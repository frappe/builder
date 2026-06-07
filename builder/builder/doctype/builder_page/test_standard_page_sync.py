# Copyright (c) 2023, asdf and Contributors
# See license.txt

import contextlib
import unittest.mock as mock

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.utils import Block


class TestStandardPageSync(FrappeTestCase):
	"""Verify that builder_files on disk stay in sync with DB operations.

	Filesystem calls are mocked so the tests remain fast and self-contained; we
	are testing the *logic* that decides whether and what to delete/rename, not
	the underlying ``shutil`` behaviour.
	"""

	# The app must be installed on the bench so that ``frappe.get_app_path``
	# succeeds.  We use the builder app itself since it is always available.
	FIXTURE_APP = "builder"
	EXPORT_MODULE = "builder.export_import_standard_page"

	# ------------------------------------------------------------------ helpers

	@staticmethod
	def _without_developer_mode():
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
	def _with_developer_mode(self):
		frappe.conf.developer_mode = 1
		try:
			yield
		finally:
			frappe.conf.developer_mode = 0

	@contextlib.contextmanager
	def _mock_page_sync_deletes(self, resource_delete_patch: str | None = None):
		"""Mock filesystem delete handlers during page cleanup; yield the resource mock if given."""
		with contextlib.ExitStack() as stack:
			stack.enter_context(mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files"))
			resource_mock = None
			if resource_delete_patch:
				resource_mock = stack.enter_context(mock.patch(resource_delete_patch))
			yield resource_mock

	def _delete_if_exists(self, doctype: str, name: str, **kwargs):
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, ignore_permissions=True, **kwargs)

	def _delete_renamed_if_exists(self, doctype: str, old_name: str, new_name: str, **kwargs):
		actual_name = new_name if frappe.db.exists(doctype, new_name) else old_name
		self._delete_if_exists(doctype, actual_name, **kwargs)

	def _assert_page_files_delete_called_once(self, mock_delete):
		mock_delete.assert_called_once()
		self.assertEqual(mock_delete.call_args[0][1], self.FIXTURE_APP)

	def _assert_sync_delete_called_once(self, mock_delete, resource_name: str):
		mock_delete.assert_called_once()
		args = mock_delete.call_args[0]
		self.assertEqual(args[0], resource_name)
		self.assertEqual(args[1], self.FIXTURE_APP)

	def _assert_sync_delete_called(self, mock_delete, resource_name: str):
		mock_delete.assert_called()
		calls = [call[0] for call in mock_delete.call_args_list]
		self.assertIn((resource_name, self.FIXTURE_APP), calls)

	def _assert_rename_called_once(self, mock_rename, old_name: str, new_name: str):
		mock_rename.assert_called_once()
		args = mock_rename.call_args[0]
		self.assertEqual(args[0], old_name)
		self.assertEqual(args[1], new_name)
		self.assertEqual(args[2], self.FIXTURE_APP)

	def _assert_export_contains(self, mock_export, item):
		mock_export.assert_called()
		self.assertIn(item, mock_export.call_args[0][0])

	def uncheck_standard(self, page):
		page.is_standard = 0
		page.app = ""
		page.save(ignore_permissions=True)

	def make_component(self):
		with self._without_developer_mode():
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

	def make_variable(self, variable_name: str | None = None):
		variable_name = variable_name or f"test-var-{frappe.generate_hash(4)}"
		with self._without_developer_mode():
			variable = frappe.get_doc(
				{
					"doctype": "Builder Variable",
					"variable_name": variable_name,
					"type": "Color",
					"value": "#ff0000",
				}
			).insert(ignore_permissions=True)
			# Page cleanup looks up variables by the identifier extracted from blocks.
			variable.variable_name = variable.name
			variable.db_set("variable_name", variable.name, update_modified=False)
			return variable

	def _blocks_with_component(self, component):
		page_block = Block(extendedFromComponent=component.name)
		return frappe.as_json([page_block.as_dict()])

	def _blocks_with_variable(self, variable):
		# Standard page cleanup resolves variables by the name embedded in block CSS.
		page_block = Block(element="div", baseStyles={"color": f"var(--{variable.name})"})
		return frappe.as_json([page_block.as_dict()])

	def make_secondary_standard_page(self, page_title: str, blocks: str = "[]", script=None):
		"""Create another standard page without triggering export side effects."""
		with self._without_developer_mode():
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
		with self._without_developer_mode():
			blocks = "[]"
			if with_component:
				blocks = self._blocks_with_component(with_component)
			elif with_variable:
				blocks = self._blocks_with_variable(with_variable)

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

	def test_on_trash_standard_page_removes_directory(self):
		page = self.make_page("trash-sync-page")
		with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files") as mock_delete:
			with self._with_developer_mode():
				page.delete(ignore_permissions=True)
			self._assert_page_files_delete_called_once(mock_delete)

	def test_on_trash_standard_page_removes_orphaned_script(self):
		page, script = self.make_page("trash-sync-page-script", with_script=True)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self._with_developer_mode():
					page.delete(ignore_permissions=True)
				self._assert_sync_delete_called_once(mock_del_script, script.name)
		finally:
			self._delete_if_exists("Builder Client Script", script.name)

	def test_on_trash_shared_script_is_not_removed(self):
		page1, script = self.make_page("trash-shared-page-1", with_script=True)
		page2 = self.make_secondary_standard_page("trash-shared-page-2", script=script)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self._with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_script.assert_not_called()
		finally:
			self._delete_if_exists("Builder Page", page2.name)
			self._delete_if_exists("Builder Client Script", script.name)

	def test_after_rename_standard_page_renames_directory(self):
		page = self.make_page("rename-sync-page-old")
		new_name = f"rename-sync-page-new-{frappe.generate_hash(4)}"
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.rename_standard_page_files") as mock_rename:
				with self._with_developer_mode():
					frappe.rename_doc("Builder Page", page.name, new_name, force=True)
				self._assert_rename_called_once(mock_rename, page.name, new_name)
		finally:
			self._delete_if_exists("Builder Page", new_name)
			self._delete_if_exists("Builder Page", page.name)

	def test_uncheck_standard_page_removes_files(self):
		page = self.make_page("uncheck-std-page")
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_page_files") as mock_delete:
				with self._with_developer_mode():
					self.uncheck_standard(page)
				self._assert_page_files_delete_called_once(mock_delete)
		finally:
			self._delete_if_exists("Builder Page", page.name, force=True)

	def test_uncheck_standard_page_removes_orphaned_scripts(self):
		page, script = self.make_page("uncheck-std-scripts", with_script=True)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self._with_developer_mode():
					self.uncheck_standard(page)
				self._assert_sync_delete_called_once(mock_del_script, script.name)
		finally:
			self._delete_if_exists("Builder Page", page.name, force=True)
			self._delete_if_exists("Builder Client Script", script.name)

	def test_client_script_on_trash_removes_directory(self):
		page, script = self.make_page("cs-trash-page", with_script=True)
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_client_script_files") as mock_del:
				with self._with_developer_mode():
					script_name = script.name
					frappe.delete_doc("Builder Client Script", script_name, force=1)
				self._assert_sync_delete_called_once(mock_del, script_name)
		finally:
			self._delete_if_exists("Builder Page", page.name)

	def test_client_script_after_rename_renames_directory(self):
		page, script = self.make_page("cs-rename-page", with_script=True)
		old_script_name = script.name
		new_script_name = f"renamed-{frappe.generate_hash(4)}"
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.rename_standard_client_script_files") as mock_rename:
				with self._with_developer_mode():
					frappe.rename_doc("Builder Client Script", old_script_name, new_script_name, force=True)
				self._assert_rename_called_once(mock_rename, old_script_name, new_script_name)
		finally:
			self._delete_renamed_if_exists("Builder Client Script", old_script_name, new_script_name, force=1)
			self._delete_if_exists("Builder Page", page.name)

	# -------------------------------------------------------- component tests

	def test_component_on_trash_removes_exported_files(self):
		component = self.make_component()
		with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_component_files") as mock_delete:
			with self._with_developer_mode():
				frappe.delete_doc("Builder Component", component.name, force=1)
			self._assert_sync_delete_called(mock_delete, component.name)

	def test_component_after_rename_removes_old_exported_files(self):
		component = self.make_component()
		old_name = component.name
		new_name = f"renamed-comp-{frappe.generate_hash(4)}"
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_component_files") as mock_delete:
				with self._with_developer_mode():
					frappe.rename_doc("Builder Component", old_name, new_name, force=True)
				self._assert_sync_delete_called(mock_delete, old_name)
		finally:
			self._delete_renamed_if_exists("Builder Component", old_name, new_name, force=1)

	def test_component_on_update_exports_to_referencing_standard_pages(self):
		component = self.make_component()
		page = self.make_page("comp-update-page", with_component=component)
		try:
			with (
				mock.patch(f"{self.EXPORT_MODULE}.export_components") as mock_export,
				mock.patch.object(type(component), "queue_action"),
			):
				with self._with_developer_mode():
					component.block = Block(element="section", blockId="comp-block-2").as_json()
					component.save(ignore_permissions=True)
				self._assert_export_contains(mock_export, component.component_id)
		finally:
			self._delete_if_exists("Builder Page", page.name)
			self._delete_if_exists("Builder Component", component.name, force=1)

	def test_on_trash_standard_page_removes_orphaned_component(self):
		component = self.make_component()
		page = self.make_page("trash-sync-page-component", with_component=component)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_component_files"
			) as mock_del_component:
				with self._with_developer_mode():
					page.delete(ignore_permissions=True)
				self._assert_sync_delete_called_once(mock_del_component, component.name)
		finally:
			self._delete_if_exists("Builder Component", component.name, force=1)

	def test_on_trash_shared_component_is_not_removed(self):
		component = self.make_component()
		page1 = self.make_page("trash-shared-comp-page-1", with_component=component)
		page2 = self.make_secondary_standard_page(
			"trash-shared-comp-page-2",
			blocks=self._blocks_with_component(component),
		)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_component_files"
			) as mock_del_component:
				with self._with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_component.assert_not_called()
		finally:
			self._delete_if_exists("Builder Page", page2.name)
			self._delete_if_exists("Builder Component", component.name, force=1)

	def test_uncheck_standard_page_removes_orphaned_component(self):
		component = self.make_component()
		page = self.make_page("uncheck-std-component", with_component=component)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_component_files"
			) as mock_del_component:
				with self._with_developer_mode():
					self.uncheck_standard(page)
				self._assert_sync_delete_called_once(mock_del_component, component.name)
		finally:
			self._delete_if_exists("Builder Page", page.name, force=True)
			self._delete_if_exists("Builder Component", component.name, force=1)

	def test_uncheck_standard_page_shared_component_is_not_removed(self):
		component = self.make_component()
		page1 = self.make_page("uncheck-shared-comp-page-1", with_component=component)
		page2 = self.make_secondary_standard_page(
			"uncheck-shared-comp-page-2",
			blocks=self._blocks_with_component(component),
		)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_component_files"
			) as mock_del_component:
				with self._with_developer_mode():
					self.uncheck_standard(page1)
				mock_del_component.assert_not_called()
		finally:
			self._delete_if_exists("Builder Page", page1.name, force=True)
			self._delete_if_exists("Builder Page", page2.name)
			self._delete_if_exists("Builder Component", component.name, force=1)

	# --------------------------------------------------------- variable tests

	def test_variable_on_trash_removes_exported_files(self):
		variable = self.make_variable()
		with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_variable_files") as mock_delete:
			with self._with_developer_mode():
				frappe.delete_doc("Builder Variable", variable.name, force=1)
			self._assert_sync_delete_called(mock_delete, variable.name)

	def test_variable_after_rename_removes_old_exported_files(self):
		variable = self.make_variable()
		old_name = variable.name
		new_name = f"renamed-var-{frappe.generate_hash(4)}"
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.delete_standard_variable_files") as mock_delete:
				with self._with_developer_mode():
					frappe.rename_doc("Builder Variable", old_name, new_name, force=True)
				self._assert_sync_delete_called(mock_delete, old_name)
		finally:
			self._delete_renamed_if_exists("Builder Variable", old_name, new_name, force=1)

	def test_variable_on_update_exports_to_referencing_standard_pages(self):
		variable = self.make_variable()
		page = self.make_page("var-update-page", with_variable=variable)
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.export_variables") as mock_export:
				with self._with_developer_mode():
					variable.value = "#00ff00"
					variable.save(ignore_permissions=True)
				self._assert_export_contains(mock_export, variable.name)
		finally:
			self._delete_if_exists("Builder Page", page.name)
			self._delete_if_exists("Builder Variable", variable.name, force=1)

	def test_variable_uncheck_is_standard_removes_module_export(self):
		variable = self.make_variable()
		variable.is_standard = 1
		variable.save(ignore_permissions=True)
		try:
			with mock.patch(
				"builder.builder.doctype.builder_variable.builder_variable.delete_folder"
			) as mock_delete_folder:
				with self._with_developer_mode():
					variable.is_standard = 0
					variable.save(ignore_permissions=True)
				mock_delete_folder.assert_called_once_with("builder", "builder_variable", variable.name)
		finally:
			self._delete_if_exists("Builder Variable", variable.name, force=1)

	def test_on_trash_standard_page_removes_orphaned_variable(self):
		variable = self.make_variable()
		page = self.make_page("trash-sync-page-variable", with_variable=variable)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_variable_files"
			) as mock_del_variable:
				with self._with_developer_mode():
					page.delete(ignore_permissions=True)
				self._assert_sync_delete_called_once(mock_del_variable, variable.name)
		finally:
			self._delete_if_exists("Builder Variable", variable.name, force=1)

	def test_on_trash_shared_variable_is_not_removed(self):
		variable = self.make_variable()
		page1 = self.make_page("trash-shared-var-page-1", with_variable=variable)
		page2 = self.make_secondary_standard_page(
			"trash-shared-var-page-2",
			blocks=self._blocks_with_variable(variable),
		)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_variable_files"
			) as mock_del_variable:
				with self._with_developer_mode():
					page1.delete(ignore_permissions=True)
				mock_del_variable.assert_not_called()
		finally:
			self._delete_if_exists("Builder Page", page2.name)
			self._delete_if_exists("Builder Variable", variable.name, force=1)

	def test_uncheck_standard_page_removes_orphaned_variable(self):
		variable = self.make_variable()
		page = self.make_page("uncheck-std-variable", with_variable=variable)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_variable_files"
			) as mock_del_variable:
				with self._with_developer_mode():
					self.uncheck_standard(page)
				self._assert_sync_delete_called_once(mock_del_variable, variable.name)
		finally:
			self._delete_if_exists("Builder Page", page.name, force=True)
			self._delete_if_exists("Builder Variable", variable.name, force=1)

	def test_uncheck_standard_page_shared_variable_is_not_removed(self):
		variable = self.make_variable()
		page1 = self.make_page("uncheck-shared-var-page-1", with_variable=variable)
		page2 = self.make_secondary_standard_page(
			"uncheck-shared-var-page-2",
			blocks=self._blocks_with_variable(variable),
		)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_variable_files"
			) as mock_del_variable:
				with self._with_developer_mode():
					self.uncheck_standard(page1)
				mock_del_variable.assert_not_called()
		finally:
			self._delete_if_exists("Builder Page", page1.name, force=True)
			self._delete_if_exists("Builder Page", page2.name)
			self._delete_if_exists("Builder Variable", variable.name, force=1)

	# -------------------------------------------------- client script tests

	def test_client_script_on_update_exports_to_referencing_standard_pages(self):
		page, script = self.make_page("cs-update-page", with_script=True)
		try:
			with mock.patch(f"{self.EXPORT_MODULE}.export_client_scripts") as mock_export:
				with self._with_developer_mode():
					script.script = "// updated test"
					script.save(ignore_permissions=True)
				self._assert_export_contains(mock_export, script.name)
		finally:
			self._delete_if_exists("Builder Page", page.name)
			self._delete_if_exists("Builder Client Script", script.name)

	def test_uncheck_standard_page_shared_script_is_not_removed(self):
		page1, script = self.make_page("uncheck-shared-script-page-1", with_script=True)
		page2 = self.make_secondary_standard_page("uncheck-shared-script-page-2", script=script)
		try:
			with self._mock_page_sync_deletes(
				f"{self.EXPORT_MODULE}.delete_standard_client_script_files"
			) as mock_del_script:
				with self._with_developer_mode():
					self.uncheck_standard(page1)
				mock_del_script.assert_not_called()
		finally:
			self._delete_if_exists("Builder Page", page1.name, force=True)
			self._delete_if_exists("Builder Page", page2.name)
			self._delete_if_exists("Builder Client Script", script.name)
