"""Clone an existing website into this site during onboarding, through Frappe's clone service. Frappe Cloud v2 and
frappe.page sites only.

The service needs a key to write into this site, so a dedicated user holds a short-lived one: it is created for the
clone and disabled as soon as the clone finishes.

A frappe.page site has no System Manager at all and is reached at its editor address (frappe.page/<sub>), so there the
clone user is a Website Manager and the service is told the editor address; its API and the nonce callback answer
under that path."""

import json

import frappe
from frappe import _
from frappe.utils.password import remove_encrypted_password

from builder.public_fetch import public_session
from builder.utils import is_mounted
from builder.www._builder import get_cloud_settings

SERVICE_URL = "https://clone.frappe.page"
CLONE_USER = "clone-service@example.com"
# Website Settings and the Builder doctypes need Website Manager; the rest of the copy needs System Manager
CLONE_ROLES = ("System Manager", "Website Manager")
# a frappe.page member is a Website Manager, which covers everything the clone writes there
MOUNTED_CLONE_ROLES = ("Website Manager",)
STATE_KEY = "builder_clone"
NONCE_SECONDS = 10 * 60
LOOKS = {"clean_up", "as_is", "redesign"}
FINISHED = {"Done", "Failed", "Expired"}


@frappe.whitelist(methods=["POST"])
def start_clone(url: str, look: str = "clean_up") -> dict | None:
	only_site_managers()
	if not (is_mounted() or get_cloud_settings().get("enabled")):
		frappe.throw(_("Cloning a website is available on Frappe Cloud sites."))
	if look not in LOOKS:
		frappe.throw(_("Pick how the copy should look."))
	nonce = frappe.generate_hash(length=32)
	frappe.cache.set_value(nonce_key(nonce), 1, expires_in_sec=NONCE_SECONDS)
	payload = {
		"url": url,
		"site": site_url(),
		"nonce": nonce,
		"design": json.dumps(design_for(look)),
		"email": frappe.session.user,
		**clone_user_keys(),
	}
	started = call_service("start_into", payload)
	frappe.db.set_default(STATE_KEY, json.dumps({"clone": started["move"], "token": started["token"]}))
	return clone_status()


@frappe.whitelist()
def clone_status() -> dict | None:
	only_site_managers()
	saved = json.loads(frappe.db.get_default(STATE_KEY) or "null")
	if not saved:
		return None
	view = call_service("status", {"move": saved["clone"], "token": saved["token"]}, http="GET")
	if view.get("status") in FINISHED:
		disable_clone_user()
	return view


@frappe.whitelist(allow_guest=True, methods=["GET"])  # nosemgrep
def confirm_clone_request(nonce: str) -> bool:
	"""The clone service calls back here: only this site knows the nonce it sent."""
	key = nonce_key(nonce)
	if not frappe.cache.get_value(key):
		return False
	frappe.cache.delete_value(key)
	return True


def only_site_managers():
	frappe.only_for("Website Manager" if is_mounted() else "System Manager")


def site_url() -> str:
	"""Where the service reaches this site's API. A frappe.page editor shares its host with every other site, so
	the address carries the mount (frappe.page/<sub>); the edge forwards the scheme and host the browser used."""
	if not is_mounted():
		return frappe.utils.get_url()
	request = frappe.request
	return f"{request.scheme}://{request.host}{frappe.get_request_header('X-FP-Mount')}"


def design_for(look: str) -> dict:
	if look == "redesign":
		return {"mode": "redesign", "prompt": "The best modern website for this type of business."}
	return {"mode": look}


def clone_user_keys() -> dict:
	"""A fresh key for the clone service user. Committed now, since the service starts writing before this request ends."""
	user = frappe.get_doc("User", CLONE_USER) if frappe.db.exists("User", CLONE_USER) else new_clone_user()
	secret = frappe.generate_hash(length=15)
	user.append_roles(*(MOUNTED_CLONE_ROLES if is_mounted() else CLONE_ROLES))
	user.enabled = 1
	user.api_key = frappe.generate_hash(length=15)
	user.api_secret = secret
	user.save(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep
	return {"api_key": user.api_key, "api_secret": secret}


def new_clone_user():
	return frappe.get_doc(
		{
			"doctype": "User",
			"email": CLONE_USER,
			"first_name": "Clone service",
			"user_type": "System User",
			"send_welcome_email": 0,
		}
	).insert(ignore_permissions=True)


def disable_clone_user():
	if not frappe.db.get_value("User", CLONE_USER, "api_key"):
		return
	frappe.db.set_value("User", CLONE_USER, {"enabled": 0, "api_key": None})
	remove_encrypted_password("User", CLONE_USER, "api_secret")


def call_service(endpoint: str, payload: dict, http: str = "POST") -> dict:
	url = f"{frappe.conf.get('builder_clone_service_url') or SERVICE_URL}/api/method/moveday.api.{endpoint}"
	session = public_session()
	if http == "GET":
		response = session.get(url, params=payload, timeout=30)
	else:
		response = session.post(url, json=payload, timeout=120)
	data = response.json()
	if response.status_code >= 400:
		frappe.throw(service_error(data) or _("The clone service couldn't do that right now."))
	return data.get("message") or {}


def service_error(data: dict) -> str | None:
	"""The first message a Frappe error response carries."""
	for raw in json.loads(data.get("_server_messages") or "[]"):
		message = json.loads(raw).get("message")
		if message:
			return message
	return None


def nonce_key(nonce: str) -> str:
	return f"builder_clone_nonce:{nonce}"
