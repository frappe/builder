"""HTTP fetches of user supplied URLs that can only ever reach the public internet.

The address check runs inside the connection, on the address it is about to dial,
so it covers every redirect hop and leaves no gap between a check and a second DNS
lookup for a rebinding answer to slip into.
"""

import ipaddress
import socket

import frappe
import requests
from frappe import _
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError
from urllib3.util import connection

MAX_REDIRECTS = 5


def public_session() -> requests.Session:
	session = requests.Session()
	# a proxy dials the target itself, out of reach of the check
	session.trust_env = False
	session.max_redirects = MAX_REDIRECTS
	session.hooks["response"].append(close_redirect_body)
	adapter = PublicAddressAdapter()
	session.mount("http://", adapter)
	session.mount("https://", adapter)
	return session


def close_redirect_body(response: requests.Response, *args, **kwargs) -> None:
	# requests reads a redirect's whole body before following it, even when the caller
	# streams or bounds the final one; a closed body reads as empty
	if response.is_redirect:
		response.raw.close()


def public_addresses(hostname: str) -> list[str]:
	"""Every address the hostname resolves to, refused unless all of them are public."""
	addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(hostname, None)))
	if not all(is_public_address(address) for address in addresses):
		frappe.throw(_("Requests to private or internal addresses are not allowed."), frappe.PermissionError)
	return addresses


def is_public_address(address: str) -> bool:
	ip = ipaddress.ip_address(address)
	ip = getattr(ip, "ipv4_mapped", None) or ip
	return ip.is_global and not (ip.is_multicast or ip.is_reserved)


class PublicAddressConnection:
	def _new_conn(self):
		error = None
		for address in public_addresses(self.host):
			try:
				return connection.create_connection(
					(address, self.port),
					self.timeout,
					source_address=self.source_address,
					socket_options=self.socket_options,
				)
			except OSError as e:
				error = e
		raise NewConnectionError(self, f"Failed to establish a new connection: {error}") from error


class PublicHTTPConnection(PublicAddressConnection, HTTPConnection):
	pass


class PublicHTTPSConnection(PublicAddressConnection, HTTPSConnection):
	pass


class PublicHTTPConnectionPool(HTTPConnectionPool):
	ConnectionCls = PublicHTTPConnection


class PublicHTTPSConnectionPool(HTTPSConnectionPool):
	ConnectionCls = PublicHTTPSConnection


class PublicAddressAdapter(HTTPAdapter):
	def init_poolmanager(self, *args, **kwargs):
		super().init_poolmanager(*args, **kwargs)
		self.poolmanager.pool_classes_by_scheme = {
			"http": PublicHTTPConnectionPool,
			"https": PublicHTTPSConnectionPool,
		}
