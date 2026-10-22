# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import frappe
import requests
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation
from builder.extensions.hub import (
	MAX_METADATA_BYTES,
	assert_installable,
	hub_get,
	read_release,
)
from builder.extensions.safe_requests import BlockedRequest

EXTENSION = "acme/installing"


class StreamedResponse:
	"""A Hub response that counts how much of its body was read."""

	def __init__(self, status_code: int, size: int):
		self.status_code = status_code
		self.ok = status_code < 400
		self.size = size
		self.read = 0

	def __enter__(self):
		return self

	def __exit__(self, *exception):
		return False

	@property
	def content(self):
		self.read = self.size
		return b" " * self.size

	def json(self):
		return frappe.parse_json(self.content)

	def iter_content(self, chunk_size):
		while self.read < self.size:
			self.read += chunk_size
			yield b" " * chunk_size


class TestRetry(FrappeTestCase):
	"""A retry must not start a second job on a row whose job still runs."""

	def setUp(self):
		drop_installations(EXTENSION)
		make_installation(EXTENSION, install_state="Installing", enabled=0)

	def test_refuses_while_the_job_is_queued_or_running(self):
		with patch("builder.extensions.hub.is_job_enqueued", return_value=True):
			self.assertRaises(frappe.ValidationError, assert_installable, EXTENSION)


class TestReadRelease(FrappeTestCase):
	def release(self, protocol_version):
		return {
			"version": "1.0.0",
			"protocol_version": protocol_version,
			"manifest": {},
			"package_url": "https://example.com/package.builderext",
			"package_size": 10,
			"package_sha256": "abc",
			"status": "Published",
		}

	def test_refuses_a_newer_protocol_before_the_download(self):
		self.assertRaises(frappe.ValidationError, read_release, EXTENSION, self.release(2))

	def test_reads_a_release_of_this_protocol(self):
		self.assertEqual(read_release(EXTENSION, self.release(1)).protocol_version, 1)


class TestHubResponseCap(FrappeTestCase):
	"""A Hub body past the cap must stop the read, not fill the worker's memory first."""

	def test_stops_a_large_answer_at_the_cap(self):
		response = StreamedResponse(200, size=100 * MAX_METADATA_BYTES)
		with patch.object(requests.Session, "get", return_value=response):
			self.assertRaises(frappe.ValidationError, hub_get, "https://hub.example.com", "get_catalog", {})
		self.assertLess(response.read, 2 * MAX_METADATA_BYTES)


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

	def test_refuses_an_internal_address_before_it_connects(self):
		with self.developer_mode(False):
			for hub_url in ("http://127.0.0.1:9", "http://10.0.0.1", "http://169.254.169.254"):
				with self.subTest(hub_url=hub_url):
					self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})

	def test_developer_mode_reaches_a_local_hub(self):
		hub_url = start_local_hub(self)
		with self.developer_mode(True):
			self.assertEqual(hub_get(hub_url, "get_catalog", {}), {"ok": 1})

	def test_developer_mode_still_refuses_other_internal_addresses(self):
		with self.developer_mode(True):
			self.assertRaises(BlockedRequest, hub_get, "http://10.0.0.1", "get_catalog", {})

	def test_refuses_a_redirect_to_an_internal_address(self):
		hub_url = start_local_hub(self, status=302, headers={"Location": "http://10.0.0.1/"})
		with self.developer_mode(True):
			self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})

	def test_checks_the_address_that_the_connection_reaches(self):
		"""A name can resolve to a public address for the check, then to this machine."""
		hub_url = start_local_hub(self)
		with self.developer_mode(False), patch("builder.extensions.safe_requests.validate_request_url"):
			self.assertRaises(BlockedRequest, hub_get, hub_url, "get_catalog", {})
