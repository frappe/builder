from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import check_password, update_password

from builder.account_onboarding import is_password_needed, set_password

USER = "cloud-signup@example.com"
PASSWORD = "Builder-onboarding-42!"


class TestAccountOnboarding(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("User", USER):
			user = frappe.new_doc("User")
			user.update({"email": USER, "first_name": "Cloud"})
			user.append_roles("System Manager")
			user.insert(ignore_permissions=True)
		frappe.db.delete("__Auth", {"doctype": "User", "name": USER})
		cloud = patch("builder.account_onboarding.get_cloud_settings", return_value={"enabled": True})
		cloud.start()
		self.addCleanup(cloud.stop)
		frappe.set_user(USER)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_sets_the_password_and_makes_a_website_manager(self):
		self.assertTrue(is_password_needed())
		set_password(PASSWORD)
		self.assertEqual(check_password(USER, PASSWORD), USER)
		self.assertIn("Website Manager", frappe.get_roles(USER))
		self.assertFalse(is_password_needed())

	def test_refuses_a_user_who_has_a_password(self):
		update_password(USER, PASSWORD)
		with self.assertRaises(frappe.PermissionError):
			set_password("Another-password-42!")

	def test_refuses_outside_frappe_cloud(self):
		with patch("builder.account_onboarding.get_cloud_settings", return_value={"enabled": False}):
			self.assertFalse(is_password_needed())
			with self.assertRaises(frappe.PermissionError):
				set_password(PASSWORD)
