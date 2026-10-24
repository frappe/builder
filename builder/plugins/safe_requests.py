# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Requests that the server sends to a Builder Hub, and to the package URLs it names.

A manager sets the Hub URL, and a Hub response sets the package URL. Either one
could point the server at an internal service. So each request must reach a
public address over HTTPS. Developer mode also allows plain HTTP and this
machine, so a local Hub works.

Frappe has the same guard as `frappe.utils.safe_exec.get_safe_request_session`,
but only in releases newer than the oldest Frappe that Builder supports. Use
Frappe's guard when Builder requires such a release.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import frappe
import requests
from frappe import _
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool


class BlockedRequest(frappe.ValidationError):
	pass


def validate_request_address(ip: str) -> None:
	try:
		address = ipaddress.ip_address(ip)
	except ValueError:
		raise BlockedRequest(_("Builder cannot read the address {0}.").format(ip))

	if address.is_global or (address.is_loopback and frappe.conf.developer_mode):
		return
	raise BlockedRequest(_("Builder does not send requests to the internal address {0}.").format(ip))


def validate_request_url(url: str) -> None:
	"""Before the connection opens, so a refusal tells nothing about the port."""
	parsed = urlparse(url)
	# the Hub sends the sha256 that proves a package, so only HTTPS can carry it
	schemes = ("http", "https") if frappe.conf.developer_mode else ("https",)
	if parsed.scheme not in schemes or not parsed.hostname:
		raise BlockedRequest(_("Builder sends requests only to {0} URLs.").format(" and ".join(schemes)))

	try:
		records = socket.getaddrinfo(parsed.hostname, parsed.port, proto=socket.IPPROTO_TCP)
	except socket.gaierror:
		# the connection fails the same way, and requests reports it
		return
	for record in records:
		validate_request_address(record[4][0])


def guarded(connection_class: type) -> type:
	class GuardedConnection(connection_class):
		def _new_conn(self):
			# the name resolves again when the socket opens, so check the address it reached
			connection = super()._new_conn()
			try:
				validate_request_address(connection.getpeername()[0])
			except BlockedRequest:
				connection.close()
				raise
			return connection

	return GuardedConnection


class GuardedHTTPConnectionPool(HTTPConnectionPool):
	ConnectionCls = guarded(HTTPConnection)


class GuardedHTTPSConnectionPool(HTTPSConnectionPool):
	ConnectionCls = guarded(HTTPSConnection)


class SafeRequestAdapter(HTTPAdapter):
	def init_poolmanager(self, *args, **kwargs):
		super().init_poolmanager(*args, **kwargs)
		self.poolmanager.pool_classes_by_scheme = {
			"http": GuardedHTTPConnectionPool,
			"https": GuardedHTTPSConnectionPool,
		}

	def send(self, request, **kwargs):
		# requests calls this once for each hop, so a redirect target is checked too
		validate_request_url(request.url)
		return super().send(request, **kwargs)


def get_safe_request_session() -> requests.Session:
	session = requests.Session()
	# a proxy from the environment would connect to an address this guard never sees
	session.trust_env = False
	adapter = SafeRequestAdapter()
	session.mount("http://", adapter)
	session.mount("https://", adapter)
	return session
