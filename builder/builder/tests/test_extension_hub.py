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


def start_local_hub(test_case: FrappeTestCase) -> str:
	"""A Hub on this machine. Answers with its URL."""
	body = b'{"message": {"ok": 1}}'

	class Handler(BaseHTTPRequestHandler):
		def do_GET(self):
			self.send_response(200)
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
			for hub_url in ("http://127.0.0.1:9", "http://10.0.0.1", "http://169.254.169.254"):
				with self.subTest(hub_url=hub_url):
					self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})

	def test_developer_mode_reaches_a_local_hub(self):
		hub_url = start_local_hub(self)
		with self.developer_mode(True):
			self.assertEqual(hub_get(hub_url, "get_catalog", {}), {"ok": 1})
