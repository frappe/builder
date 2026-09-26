# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import make_installation, make_user
from builder.extensions.data import (
	MAX_PAGE_LENGTH,
	delete_doc,
	get_count,
	get_doc,
	get_list,
	insert_doc,
	update_doc,
)


def make_extension(name="acme/data", **kwargs):
	return make_installation(name, label="Data", capabilities=["data.access"], **kwargs)


def make_contact(first_name="Ada"):
	return frappe.get_doc({"doctype": "Contact", "first_name": first_name}).insert()


class TestExtensionDocuments(FrappeTestCase):
	def setUp(self):
		make_extension()

	def tearDown(self):
		frappe.db.rollback()

	def test_reads_a_list(self):
		make_contact("Grace")

		rows = get_list("acme/data", "Contact", fields=["name", "first_name"])

		self.assertIn("Grace", [row.first_name for row in rows])

	def test_data_access_never_widens_the_users_own_permission(self):
		"""The site allows the extension. Frappe still checks the user who is calling."""
		frappe.set_user(make_user())
		self.addCleanup(frappe.set_user, "Administrator")

		# not Contact, which some sites open to every role
		self.assertFalse(frappe.has_permission("Error Log", "read"))
		with self.assertRaises(frappe.PermissionError):
			get_list("acme/data", "Error Log")

	def test_refuses_an_extension_without_data_access(self):
		make_installation("acme/no-data", capabilities=[])

		self.assertRaises(frappe.PermissionError, get_list, "acme/no-data", "Contact")

	def test_counts_without_fetching(self):
		make_contact("Grace")

		self.assertGreaterEqual(get_count("acme/data", "Contact"), 1)

	def test_counts_only_what_a_filter_matches(self):
		make_contact("Grace")
		make_contact("Ada")

		self.assertEqual(get_count("acme/data", "Contact", {"first_name": "Grace"}), 1)

	def test_reads_one_document(self):
		contact = make_contact("Ada")

		self.assertEqual(get_doc("acme/data", "Contact", contact.name)["first_name"], "Ada")

	def test_inserts_a_document(self):
		inserted = insert_doc("acme/data", "Contact", {"first_name": "Hedy"})

		self.assertTrue(frappe.db.exists("Contact", inserted["name"]))

	def test_the_payload_cannot_name_another_doctype(self):
		inserted = insert_doc("acme/data", "Contact", {"doctype": "User", "first_name": "Hedy"})

		self.assertEqual(inserted["doctype"], "Contact")

	def test_updates_a_document(self):
		contact = make_contact("Ada")

		update_doc("acme/data", "Contact", contact.name, {"first_name": "Ada L"})

		self.assertEqual(frappe.db.get_value("Contact", contact.name, "first_name"), "Ada L")

	def test_an_update_is_a_patch_not_a_replacement(self):
		contact = frappe.get_doc(
			{"doctype": "Contact", "first_name": "Ada", "last_name": "Lovelace"}
		).insert()

		update_doc("acme/data", "Contact", contact.name, {"first_name": "Grace"})

		self.assertEqual(frappe.db.get_value("Contact", contact.name, "last_name"), "Lovelace")

	def test_deletes_a_document(self):
		contact = make_contact("Ada")

		delete_doc("acme/data", "Contact", contact.name)

		self.assertFalse(frappe.db.exists("Contact", contact.name))

	def test_refuses_a_page_of_every_row(self):
		"""Frappe reads 0 as "no limit", which is the one answer no extension may ask for."""
		self.assertRaises(frappe.ValidationError, get_list, "acme/data", "Contact", limit_page_length=0)

	def test_refuses_a_page_over_the_ceiling(self):
		self.assertRaises(
			frappe.ValidationError,
			get_list,
			"acme/data",
			"Contact",
			limit_page_length=MAX_PAGE_LENGTH + 1,
		)
