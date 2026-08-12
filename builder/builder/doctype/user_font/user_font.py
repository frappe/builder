# Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.caching import redis_cache


@redis_cache(ttl=60 * 60)
def get_all_user_fonts() -> list:
	return frappe.get_all("User Font", fields=["font_name", "font_file"])


class UserFont(Document):
	def after_insert(self):
		get_all_user_fonts.clear_cache()

	def on_update(self):
		get_all_user_fonts.clear_cache()

	def on_trash(self):
		get_all_user_fonts.clear_cache()

	def get_referencing_pages(self, filters: dict | None = None, fields: list[str] | None = None):
		filters = filters or {}
		fields = fields or ["name"]
		# blocks hold a font as the "fontFamily" style key, compact from the frontend and
		# spaced from frappe.as_json; inline CSS uses font-family
		patterns = [
			f'%"fontFamily":"{self.font_name}"%',
			f'%"fontFamily": "{self.font_name}"%',
			f"%font-family:{self.font_name}%",
		]

		return frappe.get_all(
			"Builder Page",
			filters=filters,
			fields=fields,
			or_filters=[
				[block_field, "like", pattern]
				for block_field in ("blocks", "draft_blocks")
				for pattern in patterns
			],
		)
