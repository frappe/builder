import sys
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.www._builder import get_context

CLOUD_SETTINGS = "frappe.integrations.frappe_providers.cloud_settings"


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

	def test_builder_path_comes_from_the_current_site(self):
		with patch.dict(frappe.local.conf, builder_path="studio"):
			self.assertEqual(self.editor_context(dev_server=0).builder_path, "studio")

	def test_boot_carries_the_cloud_settings_context(self):
		with patch(f"{CLOUD_SETTINGS}.get_boot_context", return_value={"enabled": True}):
			self.assertEqual(self.editor_context(dev_server=0).boot["cloud_settings"], {"enabled": True})

	def test_the_editor_opens_on_a_frappe_without_cloud_settings(self):
		# a None entry makes the import fail, as it does on frappe v15
		with patch.dict(sys.modules, {CLOUD_SETTINGS: None}):
			self.assertEqual(self.editor_context(dev_server=0).boot["cloud_settings"], {"enabled": False})
