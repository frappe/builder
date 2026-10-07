# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
)
from builder.extensions.tokens import set_extension_tokens, unset_extension_token


class TestExtensionTokens(FrappeTestCase):
	def setUp(self):
		self.extension = "acme/material"
		make_installation(self.extension, label="Material")

		# a token insert clears a page cache, which commits, so a rollback between
		# tests does not reach these rows. Each test starts from none of its own
		for row in frappe.get_all("Builder Token", filters={"extension": ("like", "acme/%")}, pluck="name"):
			frappe.delete_doc("Builder Token", row, force=True)

	def tokens_of(self, extension=None):
		return frappe.get_all(
			"Builder Token",
			filters={"extension": extension or self.extension},
			fields=["name", "key", "token_name", "value", "dark_value", "group"],
		)

	def shade(self, key="accent-0", **over):
		return {"key": key, "token_name": "Accent 0", "type": "Color", "value": "#4285f4", **over}

	def test_creates_a_token(self):
		set_extension_tokens(self.extension, [self.shade()])

		rows = self.tokens_of()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["key"], "accent-0")
		self.assertEqual(rows[0]["value"], "#4285f4")

	def test_updates_in_place_rather_than_piling_up(self):
		set_extension_tokens(self.extension, [self.shade()])
		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		rows = self.tokens_of()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["value"], "#ea4335")

	def test_leaves_an_unmentioned_token_alone(self):
		set_extension_tokens(self.extension, [self.shade(), self.shade(key="accent-1")])
		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		self.assertEqual(len(self.tokens_of()), 2)

	def test_unset_removes_one_token(self):
		set_extension_tokens(self.extension, [self.shade(), self.shade(key="accent-1")])
		unset_extension_token(self.extension, "accent-1")

		self.assertEqual([row["key"] for row in self.tokens_of()], ["accent-0"])

	def test_keeps_one_extension_out_of_another(self):
		other = "acme/other-palette"
		make_installation(other, label="Other")
		set_extension_tokens(self.extension, [self.shade()])
		set_extension_tokens(other, [self.shade(value="#34a853")])

		self.assertEqual(len(self.tokens_of()), 1)
		self.assertEqual(self.tokens_of(other)[0]["value"], "#34a853")

	def installation_name(self):
		return frappe.db.get_value(INSTALLATION_DOCTYPE, {"extension": self.extension}, "name")

	def test_refuses_a_token_with_no_key(self):
		with self.assertRaises(frappe.ValidationError):
			set_extension_tokens(self.extension, [self.shade(key="")])

	def test_refuses_an_extension_the_site_has_not_installed(self):
		drop_installations("acme/never-installed")

		with self.assertRaises(frappe.PermissionError):
			set_extension_tokens("acme/never-installed", [self.shade()])

	def test_refuses_an_extension_without_the_permission(self):
		make_installation("acme/ungranted", permissions=["page.edit"])

		with self.assertRaises(frappe.PermissionError):
			set_extension_tokens("acme/ungranted", [self.shade()])
