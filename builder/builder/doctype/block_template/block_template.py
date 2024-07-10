# Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import shutil

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files

from builder.builder.doctype.builder_page.builder_page import get_template_assets_folder_path


class BlockTemplate(Document):
	def before_save(self):
		if not self.preview:
			frappe.throw(_("Preview Image is mandatory"))

		files = frappe.get_all("File", filters={"file_url": self.preview}, fields=["name"])
		if files:
			_file = frappe.get_doc("File", files[0].name)
			assets_folder_path = get_template_assets_folder_path(self)
			shutil.copy(_file.get_full_path(), assets_folder_path)
			self.preview = f"/builder_assets/{self.name}/{self.preview.split('/')[-1]}"
			self.db_set("preview", self.preview)

		export_to_files(
			record_list=[
				[
					"Block Template",
					self.name,
					"builder_block_template",
				],
			],
			record_module="builder",
		)
