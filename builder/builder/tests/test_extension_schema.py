# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_page_reader,
	make_role,
	make_user,
)
from builder.extensions.schema import (
	create_doctype,
	delete_doctype,
	get_access_change,
	get_doctype,
	set_doctype_access,
	update_doctype,
)

NAME = "Sample Widget"
RENAMED = "Sample Gadget"


def make_extension(name="acme/schema", **kwargs):
	return make_installation(name, label="Schema", permissions=["schema.write", "data.access"], **kwargs)


def a_field(**over):
	return {"fieldname": "title", "label": "Title", "fieldtype": "Data", **over}


EXTENSIONS = ("acme/schema", "acme/other", "acme/idle")
TEST_ROLES = ("Extension Page Writer", "Extension Custom Writer")


def clean_up():
	"""Creating a doctype runs DDL, and DDL commits the transaction in MariaDB.

	So `db.rollback()` cannot undo an insert that happened before one, and every
	record this file makes has to be removed by hand. A resource row outlives an
	uninstall now, so it goes separately.
	"""
	for doctype in (NAME, RENAMED):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True)
		# deleting a custom DocType keeps its table, and a rename cannot reuse that name
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{doctype}`")
	for name in EXTENSIONS:
		drop_installations(name)
		frappe.db.delete("Builder Extension Resource", {"extension": name})
	# a test's Builder Page row is committed by the DDL above, so its own cleanup cannot undo it
	frappe.db.delete("Custom DocPerm", {"parent": "Builder Page", "role": ("in", TEST_ROLES)})
	frappe.clear_cache(doctype="Builder Page")
	frappe.db.commit()


class TestExtensionSchema(FrappeTestCase):
	def setUp(self):
		clean_up()
		self.extension = make_extension()

	def tearDown(self):
		frappe.set_user("Administrator")
		clean_up()

	def create(self, **over):
		return create_doctype("acme/schema", NAME, [a_field()], **over)

	def test_creates_a_doctype(self):
		self.create()

		self.assertTrue(frappe.db.exists("DocType", NAME))

	def test_what_it_makes_is_always_custom(self):
		"""A non-custom doctype needs developer mode and writes files (doctype.py:334)."""
		self.create()

		self.assertTrue(frappe.db.get_value("DocType", NAME, "custom"))

	def test_ownership_is_recorded(self):
		self.create()

		self.assertTrue(
			frappe.db.exists(
				"Builder Extension Resource",
				{"extension": "acme/schema", "resource_type": "DocType", "resource_name": NAME},
			)
		)

	def test_a_field_type_it_cannot_add_is_refused(self):
		"""A Table needs a child doctype, so it is not on the list."""
		self.assertRaises(
			frappe.ValidationError,
			create_doctype,
			"acme/schema",
			NAME,
			[a_field(fieldtype="Table", options="Contact")],
		)

	def test_a_name_with_a_path_separator_is_refused(self):
		self.assertRaises(frappe.ValidationError, create_doctype, "acme/schema", "Sample/Widget", [a_field()])

	def test_a_name_already_taken_is_refused(self):
		self.assertRaises(frappe.ValidationError, create_doctype, "acme/schema", "Contact", [a_field()])

	def test_reading_a_doctype_needs_the_users_own_read_permission(self):
		frappe.set_user(make_page_reader(self))

		self.assertRaises(frappe.PermissionError, get_doctype, "acme/schema", "Error Log")

	def test_update_adds_a_field(self):
		self.create()

		update_doctype("acme/schema", NAME, [a_field(fieldname="note", label="Note")])

		self.assertIn("note", [field.fieldname for field in frappe.get_meta(NAME).fields])

	def test_update_never_removes_a_field_it_leaves_unmentioned(self):
		"""Removing a field drops a column and the data in it."""
		self.create()

		update_doctype("acme/schema", NAME, [a_field(fieldname="note", label="Note")])

		self.assertIn("title", [field.fieldname for field in frappe.get_meta(NAME).fields])

	def test_only_the_maker_may_change_a_doctype(self):
		"""`data.access` says nothing about reshaping the table."""
		self.create()
		make_extension("acme/other")

		self.assertRaises(
			frappe.PermissionError, update_doctype, "acme/other", NAME, [a_field(fieldname="note")]
		)

	def test_only_the_maker_may_drop_a_doctype(self):
		self.create()
		make_extension("acme/other")

		self.assertRaises(frappe.PermissionError, delete_doctype, "acme/other", NAME)

	def test_removes_one_field_and_keeps_the_other_fields_and_entries(self):
		self.create()
		update_doctype("acme/schema", NAME, [a_field(fieldname="note", label="Note")])
		entry = frappe.get_doc({"doctype": NAME, "title": "Kept", "note": "Removed"}).insert()
		update_doctype("acme/schema", NAME, [], ["note"])
		self.assertIsNone(frappe.get_meta(NAME).get_field("note"))
		self.assertEqual(frappe.db.get_value(NAME, entry.name, "title"), "Kept")

	def test_only_the_maker_may_remove_a_field(self):
		self.create()
		make_extension("acme/other")
		self.assertRaises(frappe.PermissionError, update_doctype, "acme/other", NAME, [], ["title"])

	def test_a_doctype_it_did_not_make_cannot_be_dropped(self):
		self.assertRaises(frappe.PermissionError, delete_doctype, "acme/schema", "Contact")

	def test_delete_drops_the_doctype_and_forgets_it(self):
		self.create()

		delete_doctype("acme/schema", NAME)

		self.assertFalse(frappe.db.exists("DocType", NAME))
		self.assertFalse(frappe.db.exists("Builder Extension Resource", {"resource_name": NAME}))

	def test_the_old_maker_does_not_own_a_new_doctype_with_the_same_name(self):
		"""Frappe runs no hook when a DocType is deleted in Desk, so the old row stays."""
		self.create()
		frappe.delete_doc("DocType", NAME)
		make_extension("acme/other")
		create_doctype("acme/other", NAME, [a_field()])

		self.assertRaises(
			frappe.PermissionError, update_doctype, "acme/schema", NAME, [a_field(fieldname="note")]
		)


PAGE_WRITER = "Extension Page Writer"


class TestExtensionDoctypeAccess(FrappeTestCase):
	"""Page editors use what an extension stores, so they get its doctypes too."""

	def setUp(self):
		clean_up()
		make_extension()

	def tearDown(self):
		frappe.set_user("Administrator")
		clean_up()

	def give_page_write(self, role: str):
		make_role(role)
		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				"parent": "Builder Page",
				"role": role,
				"permlevel": 0,
				"read": 1,
				"write": 1,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(doctype="Builder Page")

	def test_a_new_doctype_gives_page_editors_access(self):
		self.give_page_write(PAGE_WRITER)
		roles = create_doctype("acme/schema", NAME, [a_field()])["roles"]
		self.assertEqual(set(roles), {"System Manager", "Website Manager", PAGE_WRITER})

	def test_access_keeps_the_default_roles_and_refuses_an_administrator_only_role(self):
		# a Custom DocPerm on Builder Page replaces its standard rows, so the manager edits pages through this role
		self.give_page_write(PAGE_WRITER)
		self.give_page_write(make_custom_role("Extension Custom Writer"))
		email = make_user("extension-manager@example.com", roles=("System Manager", PAGE_WRITER))
		# the user can outlive a run, because DDL commits. So the roles are set each time
		frappe.get_doc("User", email).add_roles("System Manager", PAGE_WRITER)
		frappe.set_user(email)

		self.assertNotIn("Extension Custom Writer", create_doctype("acme/schema", NAME, [a_field()])["roles"])
		roles = set_access([])["roles"]
		self.assertEqual(set(roles), {"System Manager", "Website Manager"})
		with self.assertRaises(frappe.PermissionError):
			set_doctype_access("acme/schema", NAME, ["Extension Custom Writer"], {})

	def test_a_role_that_can_only_read_counts_as_added(self):
		create_doctype("acme/schema", NAME, [a_field()])
		document = frappe.get_doc("DocType", NAME)
		for row in document.permissions:
			if row.role == "Website Manager":
				row.update({"write": 0, "create": 0, "delete": 0})
		document.save()

		self.assertEqual(
			get_access_change("acme/schema", NAME, []), {"added": ["Website Manager"], "removed": []}
		)
		set_access([])
		self.assertEqual(get_access_change("acme/schema", NAME, []), {"added": [], "removed": []})

	def test_access_that_changed_after_the_user_saw_it_is_refused(self):
		make_role(PAGE_WRITER)
		create_doctype("acme/schema", NAME, [a_field()])
		seen = get_access_change("acme/schema", NAME, [PAGE_WRITER])
		set_access([PAGE_WRITER])

		with self.assertRaises(frappe.TimestampMismatchError):
			set_doctype_access("acme/schema", NAME, [PAGE_WRITER], seen)


def set_access(roles: list[str]) -> dict:
	"""Sets the roles with the change that the user would see."""
	return set_doctype_access("acme/schema", NAME, roles, get_access_change("acme/schema", NAME, roles))


def make_custom_role(name: str) -> str:
	"""A role marked custom, which Frappe lets only the Administrator add to a custom doctype."""
	make_role(name)
	frappe.db.set_value("Role", name, "is_custom", 1)
	return name
