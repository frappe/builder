# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
	make_user,
)
from builder.extensions.data import (
	MAX_PAGE_LENGTH,
	DoctypeGrantRequired,
	assert_doctype_grant,
	delete_doc,
	get_count,
	get_doc,
	get_doctype_grant,
	get_list,
	insert_doc,
	record_doctype_grant,
	update_doc,
	upsert_doctype_grant,
)


def make_extension(name="acme/data", **kwargs):
	return make_installation(name, label="Data", capabilities=["data.access"], **kwargs)


class TestExtensionGrants(FrappeTestCase):
	def setUp(self):
		self.extension = make_extension()

	def tearDown(self):
		frappe.db.rollback()

	def test_an_ungranted_doctype_allows_nothing(self):
		grant = get_doctype_grant("acme/data", "Contact")

		self.assertEqual(
			grant, {"doctype": "Contact", "read": "not asked", "write": "not asked", "delete": "not asked"}
		)

	def test_an_extension_this_user_has_not_installed_is_refused(self):
		"""The capability gate runs first, so there is nothing to answer about."""
		drop_installations("acme/absent")

		self.assertRaises(frappe.PermissionError, get_doctype_grant, "acme/absent", "Contact")

	def test_the_grant_belongs_to_the_copy_that_answered(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		self.assertEqual(
			frappe.db.get_value(
				"Builder Extension DocType Grant", {"document_type": "Contact"}, "installation"
			),
			self.extension.name,
		)

	def test_another_user_is_asked_again(self):
		"""One person's answer is not everybody's."""
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})
		theirs = make_user()
		make_extension(user=theirs)

		frappe.set_user(theirs)
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertEqual(get_doctype_grant("acme/data", "Contact")["read"], "not asked")

	def test_recording_a_grant_allows_what_was_asked(self):
		grant = record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		self.assertEqual(grant["read"], "allowed")
		self.assertEqual(grant["write"], "not asked")

	def test_a_second_grant_merges_with_the_first(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})
		grant = record_doctype_grant("acme/data", "Contact", {"write": "allowed"})

		self.assertEqual(grant["read"], "allowed")
		self.assertEqual(grant["write"], "allowed")

	def test_allowing_replaces_an_earlier_denial_of_the_same_access(self):
		record_doctype_grant("acme/data", "Contact", {"read": "denied"})
		grant = record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		self.assertEqual(grant["read"], "allowed")

	def test_a_denial_answers_only_the_access_it_names(self):
		record_doctype_grant("acme/data", "Contact", {"delete": "denied"})
		grant = get_doctype_grant("acme/data", "Contact")

		self.assertEqual(grant["delete"], "denied")
		self.assertEqual(grant["read"], "not asked")

	def test_a_denial_leaves_earlier_access_alone(self):
		"""Refusing write does not take back the read the user already allowed."""
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})
		grant = record_doctype_grant("acme/data", "Contact", {"write": "denied"})

		self.assertEqual(grant["read"], "allowed")
		self.assertEqual(grant["write"], "denied")
		self.assertEqual(grant["delete"], "not asked")

	def test_one_call_can_allow_and_deny_different_accesses(self):
		grant = record_doctype_grant("acme/data", "Contact", {"read": "allowed", "delete": "denied"})

		self.assertEqual((grant["read"], grant["write"], grant["delete"]), ("allowed", "not asked", "denied"))

	def test_an_answer_nobody_defined_is_refused(self):
		self.assertRaises(
			frappe.ValidationError, record_doctype_grant, "acme/data", "Contact", {"read": "maybe"}
		)

	def test_a_call_with_no_answers_is_refused(self):
		self.assertRaises(frappe.ValidationError, record_doctype_grant, "acme/data", "Contact", {})

	def test_an_unknown_access_word_is_refused(self):
		self.assertRaises(
			frappe.ValidationError, record_doctype_grant, "acme/data", "Contact", {"publish": "allowed"}
		)

	def test_one_grant_per_installation_and_doctype(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})
		record_doctype_grant("acme/data", "Contact", {"write": "allowed"})

		rows = frappe.get_all(
			"Builder Extension DocType Grant",
			filters={"installation": self.extension.name, "document_type": "Contact"},
		)
		self.assertEqual(len(rows), 1)

	def test_a_grant_is_scoped_to_one_extension(self):
		make_extension("acme/other")
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		self.assertEqual(get_doctype_grant("acme/other", "Contact")["read"], "not asked")

	def test_a_grant_is_scoped_to_one_doctype(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		self.assertEqual(get_doctype_grant("acme/data", "ToDo")["read"], "not asked")

	def test_assert_doctype_grant_passes_what_was_granted(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		assert_doctype_grant(self.extension.name, "acme/data", "Contact", "read")

	def test_assert_doctype_grant_refuses_what_was_not(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})

		self.assertRaises(
			frappe.PermissionError, assert_doctype_grant, self.extension.name, "acme/data", "Contact", "write"
		)

	def test_uninstalling_drops_only_this_users_grants(self):
		record_doctype_grant("acme/data", "Contact", {"read": "allowed"})
		theirs = make_extension(user=make_user())
		upsert_doctype_grant(theirs.name, "Contact", {"read": "allowed"})

		frappe.delete_doc(INSTALLATION_DOCTYPE, self.extension.name)

		# the two this test made, so a grant the site already held cannot fail it
		kept = frappe.get_all(
			"Builder Extension DocType Grant",
			filters={"installation": ["in", [self.extension.name, theirs.name]]},
			pluck="installation",
		)
		self.assertEqual(kept, [theirs.name])


def make_contact(first_name="Ada"):
	return frappe.get_doc({"doctype": "Contact", "first_name": first_name}).insert()


class TestExtensionDocuments(FrappeTestCase):
	def setUp(self):
		self.extension = make_extension()
		record_doctype_grant("acme/data", "Contact", {"read": "allowed", "write": "allowed"})

	def tearDown(self):
		frappe.db.rollback()

	def test_reads_a_list(self):
		make_contact("Grace")

		rows = get_list("acme/data", "Contact", fields=["name", "first_name"])

		self.assertIn("Grace", [row.first_name for row in rows])

	def test_a_list_needs_a_read_grant(self):
		self.assertRaises(DoctypeGrantRequired, get_list, "acme/data", "ToDo")

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
		"""The grant names the doctype, so a doc naming a second one is overwritten."""
		inserted = insert_doc("acme/data", "Contact", {"doctype": "User", "first_name": "Hedy"})

		self.assertEqual(inserted["doctype"], "Contact")

	def test_an_insert_needs_a_write_grant(self):
		record_doctype_grant("acme/data", "ToDo", {"read": "allowed"})

		self.assertRaises(DoctypeGrantRequired, insert_doc, "acme/data", "ToDo", {})

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

	def test_delete_needs_its_own_grant(self):
		"""Write is not enough. Losing a record is not the same as changing one."""
		contact = make_contact("Ada")

		self.assertRaises(DoctypeGrantRequired, delete_doc, "acme/data", "Contact", contact.name)

	def test_deletes_with_the_delete_grant(self):
		contact = make_contact("Ada")
		record_doctype_grant("acme/data", "Contact", {"delete": "allowed"})

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
