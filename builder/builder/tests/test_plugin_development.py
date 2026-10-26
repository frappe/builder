# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.plugin_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
	make_page_reader,
)
from builder.plugins.development import install_dev_plugin, remove_dev_plugin


class TestDevPlugin(FrappeTestCase):
	def setUp(self):
		self.plugin = "acme/development"
		drop_installations(self.plugin)
		self.previous = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		self.addCleanup(self.restore)

	def restore(self):
		frappe.conf.developer_mode = self.previous

	def installed_version(self):
		return frappe.db.get_value(INSTALLATION_DOCTYPE, {"plugin": self.plugin}, "version")

	def installed_source(self):
		return frappe.db.get_value(INSTALLATION_DOCTYPE, {"plugin": self.plugin}, "source")

	def test_registers_a_development_installation(self):
		install_dev_plugin(self.plugin)

		self.assertEqual(self.installed_version(), "0.0.0-dev")
		self.assertEqual(self.installed_source(), "Development")

	def test_removes_the_installation(self):
		install_dev_plugin(self.plugin)

		remove_dev_plugin(self.plugin)

		self.assertIsNone(self.installed_version())

	def test_refuses_an_plugin_the_site_runs(self):
		"""The editor would load both copies, and a Vue plugin cannot leave the app."""
		make_installation(self.plugin, version="1.4.0")

		with self.assertRaisesRegex(frappe.ValidationError, "Disable it"):
			install_dev_plugin(self.plugin)

	def test_refuses_a_user_who_cannot_manage_plugins(self):
		"""A development installation is the site's, like any other."""
		frappe.set_user(make_page_reader(self))
		self.addCleanup(frappe.set_user, "Administrator")

		with self.assertRaises(frappe.PermissionError):
			install_dev_plugin(self.plugin)

	def test_refuses_to_register_outside_developer_mode(self):
		frappe.conf.developer_mode = 0

		with self.assertRaises(frappe.ValidationError):
			install_dev_plugin(self.plugin)
