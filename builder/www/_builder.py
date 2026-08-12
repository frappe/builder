import frappe
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.pulse.utils import get_app_version
from frappe.translate import get_translations_from_apps, get_user_translations
from frappe.utils.telemetry import capture

from builder.hooks import builder_path

no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	context.builder_path = builder_path
	context.builder_version = get_app_version("builder")
	# developer mode
	context.is_developer_mode = frappe.conf.developer_mode
	context.is_fc_site = is_fc_site()
	context.is_read_only_mode = bool(frappe.flags.read_only)
	context.boot = get_boot()
	if frappe.session.user != "Guest":
		capture("active_site", "builder")


def get_boot() -> dict:
	# only Builder's own catalog, the editor never looks up another app's strings
	lang = frappe.local.lang
	messages = get_translations_from_apps(lang, ["builder"])
	messages.update(get_user_translations(lang) or {})
	return {"translated_messages": messages}
