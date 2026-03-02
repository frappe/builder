# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BuilderStyleBook(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		element: DF.Literal["NA", "H1", "H2", "H3", "H4", "H5", "H6", "p", "caption"]
		font_family: DF.Data | None
		font_size: DF.Data | None
		font_weight: DF.Data | None
		line_height: DF.Data | None
		style: DF.Literal[
			"None",
			"Heading 1",
			"Heading 2",
			"Heading 3",
			"Heading 4",
			"Heading 5",
			"Heading 6",
			"Paragraph",
			"Caption",
		]
	# end: auto-generated types

	pass
