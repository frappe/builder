# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation
from builder.extensions.hub import (
	MAX_METADATA_BYTES,
	assert_installable,
	hub_get,
)

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


class TestHubResponseCap(FrappeTestCase):
	"""A Hub body past the cap must stop the read, not fill the worker's memory first."""

	def test_stops_a_large_answer_at_the_cap(self):
		response = StreamedResponse(200, size=100 * MAX_METADATA_BYTES)
		with patch("builder.extensions.hub.requests.get", return_value=response):
			self.assertRaises(frappe.ValidationError, hub_get, "https://hub.example.com", "get_catalog", {})
		self.assertLess(response.read, 2 * MAX_METADATA_BYTES)
