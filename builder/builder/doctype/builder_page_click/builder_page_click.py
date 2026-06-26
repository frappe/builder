# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BuilderPageClick(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		element: DF.Data | None
		href: DF.Data | None
		is_unique: DF.Check
		path: DF.Data | None
		tag: DF.Data | None
		text: DF.Data | None
		visitor_id: DF.Data | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=180):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Builder Page Click")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))
