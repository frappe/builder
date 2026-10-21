# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import make_installation
from builder.extensions.methods import run_doc_method, run_method

EXTENSION = "acme/methods"
MODULE = "builder.builder.tests.test_extension_methods"
ECHO = f"{MODULE}.echo"


@frappe.whitelist()
def echo(word: str = "hello"):
	return word


@frappe.whitelist(methods=["GET"])
def read_echo():
	return "read"


@frappe.whitelist()
def form_dict_keys():
	return sorted(frappe.form_dict)


def not_whitelisted():
	return "never"


def make_page(route: str):
	return frappe.get_doc(
		{"doctype": "Builder Page", "page_name": route, "route": route, "blocks": "[]", "published": 1}
	).insert()


class TestExtensionMethods(FrappeTestCase):
	"""Every test method here is `builder`'s, which the floor refuses, so the floor is
	narrowed to `frappe` for these."""

	def setUp(self):
		make_installation(EXTENSION, label="Methods", permissions=["method.call"])
		floor = patch("builder.extensions.methods.REFUSED_APPS", ("frappe",))
		floor.start()
		self.addCleanup(floor.stop)

	def tearDown(self):
		frappe.db.rollback()

	def test_runs_a_method_with_its_arguments(self):
		self.assertEqual(run_method(EXTENSION, ECHO, args={"word": "hi"}), "hi")

	def test_the_method_sees_only_its_own_arguments(self):
		"""Over HTTP, form_dict holds only what the frame sent, not this wrapper's own arguments."""
		self.assertEqual(run_method(EXTENSION, f"{MODULE}.form_dict_keys", args={"word": "hi"}), ["word"])

	def test_needs_the_permission(self):
		make_installation("acme/no-methods", label="No methods", permissions=["data.access"])

		self.assertRaises(frappe.PermissionError, run_method, "acme/no-methods", ECHO)

	def test_refuses_a_method_that_is_not_whitelisted(self):
		self.assertRaises(frappe.PermissionError, run_method, EXTENSION, f"{MODULE}.not_whitelisted")

	def test_refuses_a_verb_the_method_does_not_accept(self):
		self.assertRaises(frappe.PermissionError, run_method, EXTENSION, f"{MODULE}.read_echo", "POST")
		self.assertEqual(run_method(EXTENSION, f"{MODULE}.read_echo", "GET"), "read")

	def test_refuses_a_name_that_is_not_a_dotted_path(self):
		self.assertRaises(frappe.ValidationError, run_method, EXTENSION, "upload_file")

	def test_a_doc_method_runs_on_the_document_and_answers_with_it(self):
		page = make_page("method-page")

		answer = run_doc_method(EXTENSION, "Builder Page", page.name, "unpublish")

		self.assertEqual(answer["docs"][0]["name"], page.name)
		self.assertEqual(frappe.db.get_value("Builder Page", page.name, "published"), 0)

	def test_a_doc_method_takes_only_get_and_post(self):
		page = make_page("method-verb")

		self.assertRaises(
			frappe.ValidationError,
			run_doc_method,
			EXTENSION,
			"Builder Page",
			page.name,
			"unpublish",
			"DELETE",
		)


class TestExtensionMethodFloor(FrappeTestCase):
	"""No method of frappe or builder. Otherwise `method.call` would stand in for
	`data.access`, or let an extension grant itself every permission."""

	def setUp(self):
		make_installation(EXTENSION, label="Methods", permissions=["method.call"])

	def tearDown(self):
		frappe.db.rollback()

	def test_refuses_a_frappe_method(self):
		self.assertRaises(frappe.PermissionError, run_method, EXTENSION, "frappe.client.set_value")

	def test_refuses_a_builder_method(self):
		self.assertRaises(
			frappe.PermissionError,
			run_method,
			EXTENSION,
			"builder.extensions.installations.set_granted_permissions",
		)

	def test_refuses_a_method_of_a_frappe_doctype(self):
		self.assertRaises(
			frappe.PermissionError, run_doc_method, EXTENSION, "User", "Administrator", "reset_password"
		)
