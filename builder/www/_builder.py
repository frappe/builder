import frappe

no_cache = 1
from frappe.utils.telemetry import capture


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	context.builder_path = frappe.get_conf().get("builder_path") or "builder"
	# developer mode
	context.is_developer_mode = frappe.conf.developer_mode
	if frappe.session.user != "Guest":
		capture("active_site", "builder")
