# Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BuilderProjectFolder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		folder_name: DF.Data | None
		is_standard: DF.Check
	# end: auto-generated types

	def validate(self):
		"""Validate that standard folders cannot be edited if not in developer mode"""
		if self.is_standard and not frappe.conf.get("developer_mode"):
			if not is_system_activity():
				frappe.throw(
					frappe._(
						"Standard folders cannot be modified. Please enable developer mode to edit standard folders."
					),
					frappe.PermissionError,
				)

	def on_trash(self):
		"""Prevent deletion of standard folders when not in developer mode"""
		if self.is_standard and not frappe.conf.get("developer_mode"):
			if not is_system_activity():
				frappe.throw(
					frappe._(
						"Standard folders cannot be deleted. Please enable developer mode to delete standard folders."
					),
					frappe.PermissionError,
				)


def is_system_activity():
	return (
		frappe.flags.in_import
		or frappe.flags.in_patch
		or frappe.flags.in_migrate
		or frappe.in_test
		or frappe.flags.in_install
	)
