import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import frappe
import requests
from frappe.tests.utils import FrappeTestCase

from builder.public_fetch import is_public_address, public_addresses, public_session

real_getaddrinfo = socket.getaddrinfo


class Handler(BaseHTTPRequestHandler):
	def do_GET(self):
		self.server.paths.append(self.path)
		if self.path == "/redirect":
			self.send_response(302)
			self.send_header("Location", f"http://internal.test:{self.server.server_port}/secret")
		elif self.path == "/stalled-redirect":
			self.send_response(302)
			self.send_header("Location", "/ok")
		else:
			self.send_response(200)
		if self.path == "/stalled-redirect":
			# promises a body it never sends, so reading it can only time out
			self.send_header("Content-Length", "1000000")
			self.end_headers()
			self.wfile.flush()
			time.sleep(3)
			return
		self.send_header("Content-Length", "0")
		self.end_headers()

	def log_message(self, *args):
		pass


class TestPublicSession(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
		cls.server.paths = []
		threading.Thread(target=cls.server.serve_forever, daemon=True).start()

	@classmethod
	def tearDownClass(cls):
		cls.server.shutdown()
		cls.server.server_close()
		super().tearDownClass()

	def setUp(self):
		self.server.paths.clear()
		self.lookups = []
		# the test server is on loopback, so stand it in for a public host
		patcher = patch("builder.public_fetch.is_public_address", side_effect=lambda a: a == "127.0.0.1")
		patcher.start()
		self.addCleanup(patcher.stop)

	def resolving(self, answers: dict[str, list[str]]):
		def getaddrinfo(host, *args, **kwargs):
			if host in answers:
				self.lookups.append(host)
				host = answers[host].pop(0) if len(answers[host]) > 1 else answers[host][0]
			return real_getaddrinfo(host, *args, **kwargs)

		return patch("socket.getaddrinfo", getaddrinfo)

	def url(self, path: str, host: str = "public.test", port: int | None = None) -> str:
		return f"http://{host}:{port or self.server.server_port}{path}"

	def test_fetches_a_public_address(self):
		with self.resolving({"public.test": ["127.0.0.1"]}):
			response = public_session().get(self.url("/ok"), timeout=5)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(self.server.paths, ["/ok"])

	def test_refuses_a_redirect_to_an_internal_address(self):
		with self.resolving({"public.test": ["127.0.0.1"], "internal.test": ["10.0.0.1"]}):
			self.assertRaises(frappe.PermissionError, public_session().get, self.url("/redirect"), timeout=5)

		self.assertEqual(self.server.paths, ["/redirect"])

	def test_dials_the_address_it_checked(self):
		with self.resolving({"rebind.test": ["127.0.0.1", "10.0.0.1"]}):
			response = public_session().get(self.url("/ok", host="rebind.test"), timeout=5)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(self.lookups, ["rebind.test"])

	def test_follows_a_redirect_without_reading_its_body(self):
		with self.resolving({"public.test": ["127.0.0.1"]}):
			response = public_session().get(self.url("/stalled-redirect"), stream=True, timeout=(5, 1))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(self.server.paths, ["/stalled-redirect", "/ok"])

	def test_reports_a_refused_connection(self):
		with socket.socket() as probe:
			probe.bind(("127.0.0.1", 0))
			closed_port = probe.getsockname()[1]

		with self.resolving({"public.test": ["127.0.0.1"]}):
			self.assertRaises(
				requests.ConnectionError, public_session().get, self.url("/", port=closed_port), timeout=5
			)


class TestPublicAddresses(FrappeTestCase):
	def test_refuses_a_host_with_any_internal_address(self):
		answers = [(2, 1, 6, "", ("93.184.216.34", 0)), (2, 1, 6, "", ("10.0.0.1", 0))]
		with patch("socket.getaddrinfo", return_value=answers):
			self.assertRaises(frappe.PermissionError, public_addresses, "mixed.test")

	def test_tells_public_from_internal_addresses(self):
		for address in ("93.184.216.34", "104.16.0.1", "2606:4700::1"):
			self.assertTrue(is_public_address(address), address)
		for address in (
			"127.0.0.1",
			"10.0.0.1",
			"172.16.0.1",
			"192.168.1.1",
			"169.254.169.254",
			"100.100.100.200",
			"0.0.0.0",
			"224.0.0.1",
			"::1",
			"fd00:ec2::254",
			"::ffff:127.0.0.1",
			"64:ff9b::a9fe:a9fe",
		):
			self.assertFalse(is_public_address(address), address)
