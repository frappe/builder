# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_extension_doctype_grant.builder_extension_doctype_grant import (
	TABLE,
	UNIQUE_INDEX,
	on_doctype_update,
)


class TestBuilderExtensionDocTypeGrant(FrappeTestCase):
	def test_adds_the_unique_index_once(self):
		on_doctype_update()
		on_doctype_update()

		self.assertTrue(frappe.db.has_index(TABLE, UNIQUE_INDEX))
