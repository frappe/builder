import frappe
from frappe import _
from frappe.integrations.frappe_providers.frappecloud_billing import get_base_url, get_headers
from frappe.utils.telemetry import capture

# The Frappe Cloud domain status for each Pilot certificate state.
PILOT_CERTIFICATE_STATUSES = {
	"not_required": "Active",
	"issued": "Active",
	"pending": "Pending",
	"missing": "Broken",
}


def fc_call(method: str, **params):
	frappe.only_for("System Manager")

	import requests

	response = requests.post(
		f"{get_base_url()}/api/method/press.saas.api.domain.{method}",
		headers=get_headers(),
		json=params or None,
	)

	if response.status_code != 200:
		import json as _json

		body = response.json()
		server_msgs = body.get("_server_messages")
		if server_msgs:
			try:
				msgs = _json.loads(server_msgs)
				error = (
					_json.loads(msgs[0]).get("message")
					if isinstance(msgs[0], str)
					else msgs[0].get("message")
				)
			except Exception:
				error = None
		else:
			error = body.get("exception") or body.get("message")
		frappe.throw(error or _("FC API returned {0}").format(response.status_code))

	return response.json().get("message")


def is_pilot_site() -> bool:
	try:
		from frappe.integrations.frappe_providers.cloud_settings import is_v2_site
	except ImportError:  # Cloud Settings shipped with frappe v16
		return False
	return is_v2_site()


def call_domain_api(method: str, **params):
	"""Call Frappe Cloud's domain API on a v1 site, and its Pilot equivalent on a v2 site."""
	if is_pilot_site():
		return getattr(PilotDomains(), method)(**params)
	return fc_call(method, **params)


class PilotDomains:
	"""Domains of a Frappe Cloud v2 site, which the site's Pilot manages."""

	def __init__(self):
		from frappe.integrations.frappe_providers.cloud_settings import PilotClient

		frappe.only_for("System Manager")
		self.client = PilotClient()

	def get_dns_records(self, domain: str) -> dict:
		# A domain provider can give each domain its own records, so Pilot needs the domain.
		if not domain:
			return {"cname": None, "a": None}
		records = self.client.get(self.client.domain_path(domain, "dns-records"))
		return {
			kind: next((record["value"] for record in records.get(kind) or []), None)
			for kind in ("cname", "a")
		}

	def get_domains(self) -> list[dict]:
		rows = self.client.get(self.client.site_path("domains"))["domains"]
		# Pilot cannot remove the site name, so show it only while it is primary.
		return [self.get_row(row) for row in rows if row["is_primary"] or not row["is_site"]]

	def get_row(self, row: dict) -> dict:
		return {
			"domain": row["domain"],
			"primary": row["is_primary"],
			"status": PILOT_CERTIFICATE_STATUSES[row["certificate"]],
			"redirect_to_primary": row["redirect_to_primary"],
		}

	def check_dns(self, domain: str) -> dict:
		result = self.client.get(self.client.domain_path(domain, "dns-check"))
		if not result["matched"]:
			frappe.throw(result["message"])
		return result

	def add_domain(self, domain: str) -> dict:
		return self.client.post(self.client.site_path("domains"), {"domain": domain})

	def retry_add_domain(self, domain: str) -> dict:
		# Pilot retries the setup when an attached domain is added again.
		return self.add_domain(domain)

	def remove_domain(self, domain: str) -> dict:
		return self.client.delete(self.client.domain_path(domain))

	def set_host_name(self, domain: str) -> dict:
		return self.client.patch(self.client.domain_path(domain), {"primary": True})

	def set_redirect(self, domain: str) -> dict:
		return self.client.patch(self.client.domain_path(domain), {"redirect_to_primary": True})

	def unset_redirect(self, domain: str) -> dict:
		return self.client.patch(self.client.domain_path(domain), {"redirect_to_primary": False})


@frappe.whitelist()
def get_dns_records(domain: str = "") -> dict:
	if is_pilot_site():
		return PilotDomains().get_dns_records(domain)
	# Every domain of a Frappe Cloud v1 site points to the same site and server.
	return {"cname": frappe.local.site, "a": fc_call("get_inbound_ip")}


@frappe.whitelist()
def get_domains() -> list:
	return call_domain_api("get_domains")


@frappe.whitelist()
def check_dns(domain: str) -> dict:
	return call_domain_api("check_dns", domain=domain)


@frappe.whitelist()
def add_domain(domain: str) -> str:
	result = call_domain_api("add_domain", domain=domain)
	capture("builder_custom_domain_added", "builder")
	return result


@frappe.whitelist()
def remove_domain(domain: str) -> str:
	return call_domain_api("remove_domain", domain=domain)


@frappe.whitelist()
def retry_add_domain(domain: str) -> str:
	return call_domain_api("retry_add_domain", domain=domain)


@frappe.whitelist()
def set_host_name(domain: str) -> str:
	result = call_domain_api("set_host_name", domain=domain)
	capture("builder_custom_domain_set_primary", "builder")
	return result


@frappe.whitelist()
def set_redirect(domain: str) -> str:
	return call_domain_api("set_redirect", domain=domain)


@frappe.whitelist()
def unset_redirect(domain: str) -> str:
	return call_domain_api("unset_redirect", domain=domain)
