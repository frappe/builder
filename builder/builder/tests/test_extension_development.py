# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
	make_page_reader,
)
from builder.extensions.constants import PERMISSIONS
from builder.extensions.development import install_dev_extension, remove_dev_extension
from builder.extensions.tokens import set_extension_tokens


class TestDevExtension(FrappeTestCase):
	def setUp(self):
		self.extension = "acme/development"
		drop_installations(self.extension)
		self.previous = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		self.addCleanup(self.restore)

	def restore(self):
		frappe.conf.developer_mode = self.previous

	def installed(self):
		return frappe.db.get_value(
			INSTALLATION_DOCTYPE,
			{"extension": self.extension},
			["version", "granted_permissions"],
			as_dict=True,
		)

	def test_registers_an_installation_the_gate_accepts(self):
		install_dev_extension(self.extension, ["page.edit", "token.write"])

		installed = self.installed()
		self.assertEqual(installed.version, "0.0.0-dev")
		self.assertEqual(frappe.parse_json(installed.granted_permissions), ["page.edit", "token.write"])

	def test_grants_only_what_the_manifest_asks_for(self):
		"""The gate reads this list, so a wider one would name what nobody allowed."""
		granted = install_dev_extension(self.extension, ["page.edit"])

		self.assertEqual(granted, ["page.edit"])
		self.assertNotEqual(granted, list(PERMISSIONS))

	def test_refuses_a_permission_builder_does_not_have(self):
		with self.assertRaises(frappe.ValidationError):
			install_dev_extension(self.extension, ["quantum.read"])

	def test_removes_the_installation(self):
		install_dev_extension(self.extension, ["page.edit"])

		remove_dev_extension(self.extension)

		self.assertIsNone(self.installed())

	def test_removes_the_tokens_of_the_session(self):
		install_dev_extension(self.extension, ["token.write"])
		set_extension_tokens(
			self.extension, [{"key": "a", "token_name": "A", "type": "Color", "value": "#fff"}]
		)

		remove_dev_extension(self.extension)

		self.assertFalse(frappe.db.exists("Builder Token", {"extension": self.extension}))

	def test_leaves_a_real_installation_alone(self):
		"""The name may belong to an extension the site really installed."""
		make_installation(self.extension, version="1.4.0")

		remove_dev_extension(self.extension)

		self.assertEqual(self.installed().version, "1.4.0")

	def test_refuses_a_user_who_cannot_manage_extensions(self):
		"""A development installation is the site's, like any other."""
		frappe.set_user(make_page_reader(self))
		self.addCleanup(frappe.set_user, "Administrator")

		with self.assertRaises(frappe.PermissionError):
			install_dev_extension(self.extension)

	def test_refuses_to_register_outside_developer_mode(self):
		frappe.conf.developer_mode = 0

		with self.assertRaises(frappe.ValidationError):
			install_dev_extension(self.extension)
