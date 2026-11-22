"""Set up the account of a Frappe Cloud v2 user during onboarding.

Frappe Cloud signs the first user in without a password. Builder skips the desk setup wizard, where a user sets one,
so onboarding asks for it instead."""

import frappe
from frappe import _
from frappe.core.doctype.user.user import handle_password_test_fail, test_password_strength
from frappe.utils import today
from frappe.utils.password import update_password

from builder.www._builder import get_cloud_settings

ONBOARDING_ROLES = ("Website Manager",)


def is_password_needed() -> bool:
	# Cloud Settings is on only for a System Manager of a v2 site
	if not get_cloud_settings().get("enabled"):
		return False
	return not frappe.db.exists(
		"__Auth", {"doctype": "User", "name": frappe.session.user, "fieldname": "password"}
	)


@frappe.whitelist(methods=["POST"])
def set_password(new_password: str) -> None:
	# a user who has a password must give the old one to change it, which desk does
	if not is_password_needed():
		frappe.throw(_("Your account already has a password."), frappe.PermissionError)
	feedback = test_password_strength(new_password).get("feedback")
	if feedback and not feedback.get("password_policy_validation_passed", False):
		handle_password_test_fail(feedback)
	user = frappe.session.user
	update_password(user, new_password)
	frappe.db.set_value("User", user, "last_password_reset_date", today())
	frappe.get_doc("User", user).add_roles(*ONBOARDING_ROLES)
