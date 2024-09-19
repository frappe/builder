# Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import os
import shutil

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.modules import scrub
from frappe.modules.export_file import export_to_files

from builder.builder.doctype.builder_page.builder_page import get_template_assets_folder_path
from builder.utils import copy_img_to_asset_folder


class BlockTemplate(Document):
	def on_update(self):
		if not self.preview:
			frappe.throw(_("Preview Image is mandatory"))

		files = frappe.get_all("File", filters={"file_url": self.preview}, fields=["name"])
		if files:
			_file = frappe.get_doc("File", files[0].name)
			assets_folder_path = get_template_assets_folder_path(self)
			shutil.copy(_file.get_full_path(), assets_folder_path)
			self.preview = f"/builder_assets/{self.name}/{self.preview.split('/')[-1]}"
			self.db_set("preview", self.preview)

		block = frappe.parse_json(self.block)
		if block:
			copy_img_to_asset_folder(block, self)
		self.db_set("block", frappe.as_json(block, indent=None))

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

	def on_trash(self):
		block_template_folder = os.path.join(
			frappe.get_app_path("builder"), "builder", "builder_block_template", scrub(self.name)
		)
		shutil.rmtree(block_template_folder, ignore_errors=True)
		assets_folder_path = get_template_assets_folder_path(self)
		shutil.rmtree(assets_folder_path, ignore_errors=True)
