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
from builder.extensions.development import install_dev_extension, remove_dev_extension


class TestDevExtension(FrappeTestCase):
	def setUp(self):
		self.extension = "acme/development"
		drop_installations(self.extension)
		self.previous = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		self.addCleanup(self.restore)

	def restore(self):
		frappe.conf.developer_mode = self.previous

	def installed_version(self):
		return frappe.db.get_value(INSTALLATION_DOCTYPE, {"extension": self.extension}, "version")

	def test_registers_a_development_installation(self):
		install_dev_extension(self.extension)

		self.assertEqual(self.installed_version(), "0.0.0-dev")

	def test_removes_the_installation(self):
		install_dev_extension(self.extension)

		remove_dev_extension(self.extension)

		self.assertIsNone(self.installed_version())

	def test_registers_again_after_a_reload(self):
		install_dev_extension(self.extension)

		install_dev_extension(self.extension)

		self.assertEqual(self.installed_version(), "0.0.0-dev")

	def test_refuses_an_extension_the_site_runs(self):
		"""The editor would load both copies, and a plugin cannot leave the app."""
		make_installation(self.extension, version="1.4.0")

		with self.assertRaisesRegex(frappe.ValidationError, "Disable it"):
			install_dev_extension(self.extension)

	def test_leaves_a_disabled_installation_alone(self):
		"""An author can build a new release of an extension the site has installed."""
		make_installation(self.extension, version="1.4.0", enabled=0)

		install_dev_extension(self.extension)
		remove_dev_extension(self.extension)

		self.assertEqual(self.installed_version(), "1.4.0")

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
