from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.www._builder import get_context


class TestEditorPage(FrappeTestCase):
	def editor_context(self, dev_server: int) -> frappe._dict:
		context = frappe._dict()
		with patch.object(frappe, "_dev_server", dev_server), patch("builder.www._builder.capture"):
			get_context(context)
		return context

	def test_socketio_port_is_given_only_to_bench_start(self):
		with patch.dict(frappe.local.conf, socketio_port=9123):
			self.assertEqual(self.editor_context(dev_server=1).socketio_port, 9123)
			# behind a proxy socket.io shares the page's origin, so a port would bypass the proxy
			self.assertNotIn("socketio_port", self.editor_context(dev_server=0))
