# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_extension_doctype_grant.builder_extension_doctype_grant import (
	OLD_UNIQUE_INDEX,
	TABLE,
	UNIQUE_INDEX,
	on_doctype_update,
)


class TestBuilderExtensionDocTypeGrant(FrappeTestCase):
	def test_drops_the_index_that_shared_one_answer_between_copies(self):
		frappe.db.sql_ddl(
			f"alter table `{TABLE}` add unique index `{OLD_UNIQUE_INDEX}` (`installation`, `document_type`)"
		)

		on_doctype_update()

		self.assertFalse(frappe.db.has_index(TABLE, OLD_UNIQUE_INDEX))
		self.assertTrue(frappe.db.has_index(TABLE, UNIQUE_INDEX))
