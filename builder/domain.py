import re

import frappe


def dev_validate_domain(domain: str) -> str:
	"""Normalise and validate; raises ValidationError for malformed input."""
	domain = (domain or "").strip().lower()

	if not domain or "." not in domain or domain.startswith(".") or domain.endswith(".") or ".." in domain:
		frappe.throw(
			"Invalid domain format. Enter a fully qualified domain like www.example.com or example.com."
		)

	labels = domain.split(".")
	if len(labels[-1]) < 2 or any(
		not label
		or len(label) > 63
		or label.startswith("-")
		or label.endswith("-")
		or not re.match(r"^[a-z0-9-]+$", label)
		for label in labels
	):
		frappe.throw(
			"Invalid domain format. Enter a fully qualified domain like www.example.com or example.com."
		)

	return domain


def dev_load_domains() -> list:
	domains = frappe.cache().get_value("builder_site_domains")
	if domains is None:
		domains = [
			{
				"name": frappe.local.site,
				"domain": frappe.local.site,
				"status": "Active",
				"retry_count": 0,
				"redirect_to_primary": 0,
				"primary": True,
			}
		]
		frappe.cache().set_value("builder_site_domains", domains)
	return domains


def dev_save_domains(domains: list) -> None:
	frappe.cache().set_value("builder_site_domains", domains)


# ─── Frappe Cloud proxy ───────────────────────────────────────────────────────


def fc_call(method: str, **params):
	"""Proxy to press.api.developer.domain.{method} on Frappe Cloud."""
	import requests
	from frappe.integrations.frappe_providers.frappecloud_billing import get_base_url

	secret_key = frappe.conf.get("fc_subscription_secret_key")
	if not secret_key:
		frappe.throw(
			frappe._(
				"Frappe Cloud subscription secret key is not configured."
				" Set fc_subscription_secret_key in site_config.json."
			)
		)

	url = f"https://staging.frappe.cloud/api/method/press.api.developer.domain.{method}"
	response = requests.post(url, data={"secret_key": secret_key, **params})

	if response.status_code != 200:
		body = response.json()
		# Try to surface the real error from the FC response
		server_msgs = body.get("_server_messages")
		if server_msgs:
			import json as _json

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
	if frappe.conf.developer_mode:
		ip = frappe.cache().get_value("builder_site_server_ip")
		if ip is None:
			ip = "192.0.2.1"
			frappe.cache().set_value("builder_site_server_ip", ip)
		return ip
	return fc_call("get_inbound_ip")


@frappe.whitelist()
def get_domains() -> list:
	if frappe.conf.developer_mode:
		return dev_load_domains()
	return fc_call("get_domains")


@frappe.whitelist()
def check_dns(domain: str) -> dict:
	if frappe.conf.developer_mode:
		domain = dev_validate_domain(domain)
		matched = domain == frappe.local.site or domain.endswith(f".{frappe.local.site}")
		return {
			"matched": matched,
			"type": "CNAME",
			"CNAME": {"matched": matched, "answer": frappe.local.site if matched else None},
			"A": {"matched": False, "answer": None},
		}
	return fc_call("check_dns", domain=domain)


@frappe.whitelist()
def add_domain(domain: str) -> str:
	if frappe.conf.developer_mode:
		domains = dev_load_domains()
		if not any(d["domain"] == domain for d in domains):
			domains.append(
				{
					"name": domain,
					"domain": domain,
					"status": "Active",
					"retry_count": 0,
					"redirect_to_primary": 0,
					"primary": False,
				}
			)
			dev_save_domains(domains)
		return "ok"
	return fc_call("add_domain", domain=domain)


@frappe.whitelist()
def remove_domain(domain: str) -> str:
	if frappe.conf.developer_mode:
		dev_save_domains([d for d in dev_load_domains() if d["domain"] != domain])
		return "ok"
	return fc_call("remove_domain", domain=domain)


@frappe.whitelist()
def retry_add_domain(domain: str) -> str:
	if frappe.conf.developer_mode:
		domains = dev_load_domains()
		for d in domains:
			if d["domain"] == domain:
				d["status"] = "Active"
				d["retry_count"] = d.get("retry_count", 0) + 1
				break
		dev_save_domains(domains)
		return "ok"
	return fc_call("retry_add_domain", domain=domain)


@frappe.whitelist()
def set_host_name(domain: str) -> str:
	if frappe.conf.developer_mode:
		domains = dev_load_domains()
		for d in domains:
			d["primary"] = d["domain"] == domain
		dev_save_domains(domains)
		return "ok"
	return fc_call("set_host_name", domain=domain)


@frappe.whitelist()
def set_redirect(domain: str) -> str:
	if frappe.conf.developer_mode:
		domains = dev_load_domains()
		for d in domains:
			if d["domain"] == domain:
				d["redirect_to_primary"] = 1
				break
		dev_save_domains(domains)
		return "ok"
	return fc_call("set_redirect", domain=domain)


@frappe.whitelist()
def unset_redirect(domain: str) -> str:
	if frappe.conf.developer_mode:
		domains = dev_load_domains()
		for d in domains:
			if d["domain"] == domain:
				d["redirect_to_primary"] = 0
				break
		dev_save_domains(domains)
		return "ok"
	return fc_call("unset_redirect", domain=domain)
