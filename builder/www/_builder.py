import frappe
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.pulse.utils import get_app_version
from frappe.translate import get_translations_from_apps, get_user_translations
from frappe.utils.telemetry import capture
from frappe.utils.telemetry.pulse.client import is_enabled as is_telemetry_enabled

from builder.editor_demo import EditorDemo
from builder.utils import get_builder_path

no_cache = 1


def get_context(context):
	context.builder_path = get_builder_path()
	context.boot = get_boot()
	if demo := EditorDemo.from_app_path(frappe.form_dict.app_path):
		# no csrf token or session details: the demo must stay inert for signed-in visitors too
		demo.set_context(context)
		return

	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosemgrep
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	if frappe._dev_server:
		# production proxies socket.io on the page's origin, bench start runs it on a port of its own
		context.socketio_port = frappe.conf.socketio_port
	context.builder_version = get_app_version("builder")
	# developer mode
	context.is_developer_mode = frappe.conf.developer_mode
	context.is_fc_site = is_fc_site()
	context.is_read_only_mode = bool(frappe.flags.read_only)
	if frappe.session.user != "Guest":
		capture("active_site", "builder")


def get_boot() -> dict:
	# only Builder's own catalog, the editor never looks up another app's strings
	lang = frappe.local.lang
	messages = get_translations_from_apps(lang, ["builder"])
	messages.update(get_user_translations(lang) or {})
	return {
		"translated_messages": messages,
		# the trial card opens Cloud Settings with this context, so the SDK skips its own lookup
		"cloud_settings": get_cloud_settings(),
		# content blockers stop the Pulse client, so onboarding reads the server's verdict instead
		"telemetry_enabled": is_telemetry_enabled(),
	}


def get_cloud_settings() -> dict:
	try:
		from frappe.integrations.frappe_providers.cloud_settings import get_boot_context
	except ImportError:  # Cloud Settings shipped with frappe v16
		return {"enabled": False}
	return get_boot_context()
