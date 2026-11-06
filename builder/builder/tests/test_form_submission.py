import json
import re
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_page.builder_page import get_block_html
from builder.form_doctype import create_form_doctype
from builder.form_submission import (
	FormSubmission,
	list_form_doctype_fields,
	list_form_doctypes,
	seal_destinations,
	validate_form_doctype,
	validate_new_form_doctypes,
)

DOCTYPE = "Builder Test Form Entry"
SIGNUP_DOCTYPE = "Builder Test Form Signup"
USER = "form-submission-test@example.com"


def form_block(send_to: list[dict], fields: list[dict]) -> dict:
	return {
		"blockId": "form",
		"element": "form",
		"attributes": {"data-send-to": json.dumps(send_to)},
		"children": [{"element": "input", "attributes": field} for field in fields],
	}


def sealed_destinations(block: dict) -> str:
	html, _, _, _ = get_block_html([block])
	return re.search(r'data-send-to="([^"]+)"', html).group(1)


def as_user(user: str):
	frappe.set_user(user)
	return lambda: frappe.set_user("Administrator")


class TestFormSubmission(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("DocType", DOCTYPE):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": DOCTYPE,
					"module": "Builder",
					"custom": 1,
					"naming_rule": "Random",
					"fields": [
						{"fieldname": "full_name", "label": "Full Name", "fieldtype": "Data"},
						{"fieldname": "subscribe", "label": "Subscribe", "fieldtype": "Check"},
						{"fieldname": "notes", "label": "Notes", "fieldtype": "Data"},
					],
					"permissions": [{"role": "System Manager", "read": 1, "create": 1}],
				}
			).insert()
		if not frappe.db.exists("DocType", SIGNUP_DOCTYPE):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": SIGNUP_DOCTYPE,
					"module": "Builder",
					"custom": 1,
					"naming_rule": "By fieldname",
					"autoname": "field:email",
					"fields": [
						{"fieldname": "full_name", "label": "Full Name", "fieldtype": "Data", "reqd": 1},
						{"fieldname": "email", "label": "Email", "fieldtype": "Data"},
						{"fieldname": "phone", "label": "Phone", "fieldtype": "Data", "options": "Phone"},
						{"fieldname": "plan", "fieldtype": "Data", "reqd": 1, "default": "Free"},
						{"fieldname": "agreed", "label": "Agreed", "fieldtype": "Check", "reqd": 1},
						{"fieldname": "photo", "label": "Photo", "fieldtype": "Attach"},
					],
					"permissions": [{"role": "System Manager", "read": 1, "create": 1}],
				}
			).insert()
		if not frappe.db.exists("User", USER):
			frappe.get_doc({"doctype": "User", "email": USER, "first_name": "Form"}).insert()

	def test_saves_a_submission_to_its_doctype(self):
		block = form_block(
			[{"type": "doctype", "value": DOCTYPE}],
			[{"name": "full_name"}, {"name": "subscribe", "type": "checkbox", "value": "yes"}],
		)

		FormSubmission(sealed_destinations(block), {"full_name": "Ada", "subscribe": "yes"}, "/").deliver()

		entry = frappe.get_last_doc(DOCTYPE)
		self.assertEqual(entry.full_name, "Ada")
		self.assertEqual(entry.subscribe, 1)

	def test_sets_only_the_fields_the_form_has(self):
		block = form_block([{"type": "doctype", "value": DOCTYPE}], [{"name": "full_name"}])

		FormSubmission(
			sealed_destinations(block), {"full_name": "Grace", "notes": "sneaked in"}, "/"
		).deliver()

		self.assertIsNone(frappe.get_last_doc(DOCTYPE).notes)

	def test_refuses_a_value_too_long_instead_of_cutting_it_short(self):
		block = form_block([{"type": "doctype", "value": DOCTYPE}], [{"name": "full_name"}])
		count = frappe.db.count(DOCTYPE)

		with self.assertRaises(frappe.ValidationError):
			FormSubmission(sealed_destinations(block), {"full_name": "x" * 6000}, "/").deliver()

		self.assertEqual(frappe.response.pop("invalid_field")["name"], "full_name")
		self.assertEqual(frappe.db.count(DOCTYPE), count)

	def test_lists_the_fields_a_form_can_fill_and_the_ones_it_must(self):
		fields = list_form_doctype_fields(SIGNUP_DOCTYPE)

		# a form can't attach a file
		self.assertEqual([f["fieldname"] for f in fields], ["full_name", "email", "phone", "plan", "agreed"])
		# records are named after Email, and Plan and Agreed fill themselves
		self.assertEqual([f["fieldname"] for f in fields if f["needed"]], ["full_name", "email"])
		# Plan has a default, so it's the site's to set
		self.assertEqual([f["fieldname"] for f in fields if f["suggested"]], ["phone", "agreed"])

	def test_refuses_a_framework_doctype_a_page_was_saved_with(self):
		sealed = seal_destinations(json.dumps([{"type": "doctype", "value": "User"}]), ["email"])

		with self.assertRaises(frappe.PermissionError):
			FormSubmission(sealed, {"email": "guest@example.com"}, "/").deliver()

	def test_lists_doctypes_a_form_can_save_to(self):
		doctypes = list_form_doctypes()

		self.assertIn(DOCTYPE, doctypes)
		self.assertNotIn("User", doctypes)
		self.assertNotIn("Builder Page", doctypes)

	def test_refuses_the_frameworks_own_doctypes(self):
		for doctype in ("User", "Builder Client Script", "Has Role", "Missing DocType"):
			with self.assertRaises(frappe.ValidationError):
				validate_form_doctype(doctype)

	def test_needs_create_permission_to_point_a_form_at_a_doctype(self):
		blocks = json.dumps([form_block([{"type": "doctype", "value": DOCTYPE}], [])])
		restore = as_user(USER)
		try:
			with self.assertRaises(frappe.PermissionError):
				validate_new_form_doctypes((blocks,), ())
			# a form someone else already pointed there is not the editor's to answer for
			validate_new_form_doctypes((blocks,), (blocks,))
		finally:
			restore()

	def test_page_save_refuses_a_framework_doctype(self):
		blocks = [form_block([{"type": "doctype", "value": "User"}], [{"name": "email"}])]
		page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Form Test", "blocks": blocks})

		with self.assertRaisesRegex(frappe.ValidationError, "can't save its submissions to User"):
			page.insert()


class TestFormDoctype(FrappeTestCase):
	def make(self, fields: list[dict]) -> tuple[list[str], list[dict]]:
		with patch("builder.form_doctype.frappe.get_doc") as get_doc:
			fieldnames = create_form_doctype("Builder Test Made Form", fields)
		doctype = get_doc.call_args.args[0]
		self.assertEqual(doctype["custom"], 1)
		# without autoname, Frappe warns "Naming is not set", and that shows in place of a real error
		self.assertEqual(doctype["autoname"], "hash")
		return fieldnames, {field["fieldname"]: field for field in doctype["fields"]}

	def test_makes_a_field_for_each_input(self):
		fieldnames, fields = self.make(
			[
				{"fieldname": "full_name", "label": "Full Name", "fieldtype": "Data", "reqd": True},
				{"fieldname": "", "label": "Your Email", "fieldtype": "Data", "options": "Email"},
				{"fieldname": "city", "label": "City", "fieldtype": "Select", "options": "Pune\nGoa"},
				{"fieldname": "photo", "label": "Photo", "fieldtype": "Attach Image"},
			]
		)

		self.assertEqual(fieldnames, ["full_name", "your_email", "city", "photo"])
		self.assertEqual(fields["full_name"]["reqd"], 1)
		self.assertEqual(fields["your_email"]["options"], "Email")
		self.assertEqual(fields["city"]["options"], "Pune\nGoa")
		self.assertEqual(fields["photo"]["fieldtype"], "Data")

	def test_renames_a_reserved_fieldname(self):
		fieldnames, _ = self.make([{"fieldname": "name", "fieldtype": "Data"}])

		self.assertEqual(fieldnames, ["name_field"])

	def test_inputs_sharing_a_name_are_one_field(self):
		fieldnames, fields = self.make(
			[
				{"fieldname": "interests", "label": "Yoga", "fieldtype": "Check"},
				{"fieldname": "interests", "label": "Pilates", "fieldtype": "Check"},
			]
		)

		self.assertEqual(fieldnames, ["interests", "interests"])
		self.assertEqual(list(fields), ["interests"])
