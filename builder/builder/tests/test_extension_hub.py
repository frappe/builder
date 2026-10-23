# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.extensions.hub import hub_get, read_release
from builder.extensions.safe_requests import BlockedRequest


class TestReadRelease(FrappeTestCase):
	def test_refuses_a_newer_protocol_before_the_download(self):
		release = {
			"version": "1.0.0",
			"protocol_version": 2,
			"manifest": {},
			"package_url": "https://example.com/package.builderext",
			"package_size": 10,
			"package_sha256": "abc",
			"status": "Published",
		}
		self.assertRaises(frappe.ValidationError, read_release, "acme/installing", release)


def start_local_hub(test_case: FrappeTestCase, status: int = 200, headers: dict | None = None) -> str:
	"""A Hub on this machine that answers every GET the same way. Answers with its URL."""
	body = b'{"message": {"ok": 1}}'

	class Handler(BaseHTTPRequestHandler):
		def do_GET(self):
			self.send_response(status)
			for name, value in (headers or {}).items():
				self.send_header(name, value)
			self.send_header("Content-Length", str(len(body)))
			self.end_headers()
			self.wfile.write(body)

		def log_message(self, *args):
			pass

	server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
	threading.Thread(target=server.serve_forever, daemon=True).start()
	test_case.addCleanup(server.server_close)
	test_case.addCleanup(server.shutdown)
	return f"http://127.0.0.1:{server.server_port}"


class TestHubAddresses(FrappeTestCase):
	"""A Hub URL or a package URL must not reach an internal service."""

	def developer_mode(self, enabled: bool):
		return patch.dict(frappe.conf, {"developer_mode": int(enabled)})

	def test_refuses_an_internal_address(self):
		with self.developer_mode(False):
			for hub_url in ("https://127.0.0.1:9", "https://10.0.0.1", "https://169.254.169.254"):
				with self.subTest(hub_url=hub_url):
					self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})

	def test_developer_mode_reaches_a_local_hub(self):
		hub_url = start_local_hub(self)
		with self.developer_mode(True):
			self.assertEqual(hub_get(hub_url, "get_catalog", {}), {"ok": 1})

	def test_refuses_a_redirect_to_an_internal_address(self):
		hub_url = start_local_hub(self, status=302, headers={"Location": "http://10.0.0.1/"})
		with self.developer_mode(True):
			self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})

	def test_checks_the_address_that_the_connection_reaches(self):
		"""A name can resolve to a public address for the check, then to this machine."""
		hub_url = start_local_hub(self)
		with self.developer_mode(False), patch("builder.extensions.safe_requests.validate_request_url"):
			self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})
