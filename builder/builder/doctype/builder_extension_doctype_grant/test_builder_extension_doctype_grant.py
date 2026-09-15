# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import make_installation, make_user


class TestBuilderExtensionDocTypeGrant(FrappeTestCase):
	"""One installation's answer about one doctype."""

	def setUp(self):
		self.installation = make_installation("acme/grants")

	def tearDown(self):
		frappe.db.rollback()

	def grant(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Builder Extension DocType Grant",
				"installation": self.installation.name,
				"document_type": "Contact",
				**values,
			}
		)

	def test_name_is_a_uuid(self):
		"""A composite name would go stale the first time a doctype is renamed."""
		self.assertEqual(len(self.grant(read_access="allowed").insert().name), 36)

	def test_installation_must_exist(self):
		self.assertRaises(frappe.LinkValidationError, self.grant(installation="no-such-copy").insert)

	def test_document_type_must_exist(self):
		self.assertRaises(frappe.LinkValidationError, self.grant(document_type="No Such Doctype").insert)

	def test_two_users_answer_separately(self):
		"""One person allowing an extension says nothing about the next."""
		theirs = make_installation("acme/grants", user=make_user())

		mine = self.grant(read_access="allowed").insert()
		other = self.grant(installation=theirs.name, read_access="denied").insert()

		self.assertNotEqual(mine.name, other.name)
		self.assertEqual(mine.installation, self.installation.name)
