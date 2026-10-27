# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Requests that the server sends to a Builder Hub, and to the package URLs it names.

A manager sets the Hub URL, and a Hub response sets the package URL. Either one
could point the server at an internal service. `public_session` keeps each request
on a public address. A plugin request must also use HTTPS, because the Hub sends
the sha256 that proves a package. Developer mode allows plain HTTP and this
machine, so a local Hub works.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import frappe
import requests
from frappe import _
from requests.adapters import HTTPAdapter

from builder.public_fetch import PublicAddressAdapter, is_public_address, public_session


class HTTPSOnlyAdapter(PublicAddressAdapter):
	def send(self, request, **kwargs):
		# requests calls this once for each hop, so a redirect target is checked too
		if urlparse(request.url).scheme != "https":
			frappe.throw(_("Builder sends plugin requests only to HTTPS URLs."))
		return super().send(request, **kwargs)


class LocalHubAdapter(HTTPAdapter):
	"""Developer mode only. Each hop may reach this machine or a public address."""

	def send(self, request, **kwargs):
		if not all(is_hub_address(address) for address in resolve(urlparse(request.url).hostname)):
			frappe.throw(
				_("Requests to private or internal addresses are not allowed."), frappe.PermissionError
			)
		return super().send(request, **kwargs)


def resolve(hostname: str) -> set[str]:
	try:
		return {info[4][0] for info in socket.getaddrinfo(hostname, None)}
	except socket.gaierror:
		# the connection fails the same way, and requests reports it
		return set()


def is_hub_address(address: str) -> bool:
	return is_public_address(address) or ipaddress.ip_address(address).is_loopback


def get_safe_request_session() -> requests.Session:
	session = public_session()
	adapter = LocalHubAdapter() if frappe.conf.developer_mode else HTTPSOnlyAdapter()
	session.mount("http://", adapter)
	session.mount("https://", adapter)
	return session
