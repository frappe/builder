import frappe
from frappe.integrations.frappe_providers.frappecloud_billing import get_base_url, get_headers
from frappe.utils.telemetry import capture


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
		frappe.throw(error or f"FC API returned {response.status_code}")

	return response.json().get("message")


@frappe.whitelist()
def get_server_ip() -> str | None:
	return fc_call("get_inbound_ip")


@frappe.whitelist()
def get_domains() -> list:
	return fc_call("get_domains")


@frappe.whitelist()
def check_dns(domain: str) -> dict:
	return fc_call("check_dns", domain=domain)


@frappe.whitelist()
def add_domain(domain: str) -> str:
	result = fc_call("add_domain", domain=domain)
	capture("builder_custom_domain_added", "builder")
	return result


@frappe.whitelist()
def remove_domain(domain: str) -> str:
	return fc_call("remove_domain", domain=domain)


@frappe.whitelist()
def retry_add_domain(domain: str) -> str:
	return fc_call("retry_add_domain", domain=domain)


@frappe.whitelist()
def set_host_name(domain: str) -> str:
	return fc_call("set_host_name", domain=domain)


@frappe.whitelist()
def set_redirect(domain: str) -> str:
	return fc_call("set_redirect", domain=domain)


@frappe.whitelist()
def unset_redirect(domain: str) -> str:
	return fc_call("unset_redirect", domain=domain)
