import base64
import io
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from PIL import Image

from builder.ai import api, memory, workspace
from builder.ai.brief import DesignBrief, validate_asset_usage
from builder.plugins import bob


class TestWorkflowIntegrations(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Bob integration regression"}
		).insert()
		self.addCleanup(frappe.set_user, "Administrator")

	def test_restricted_users_cannot_read_each_others_memory(self):
		users = []
		for suffix in ("alice", "bob"):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": f"bob-{suffix}-{frappe.generate_hash(length=8)}@example.test",
					"first_name": suffix,
					"send_welcome_email": 0,
					"roles": [{"role": "Website Manager"}],
				}
			).insert()
			users.append(user.name)
		frappe.set_user(users[0])
		secret = frappe.get_doc(
			{"doctype": memory.DOCTYPE, "content": "Private brand direction", "scope": "user"}
		).insert()
		self.assertIn(secret.name, [row.name for row in memory.visible()])
		frappe.set_user(users[1])
		self.assertNotIn(secret.name, [row.name for row in memory.visible()])
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(memory.DOCTYPE, secret.name).check_permission("read")
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": memory.DOCTYPE, "content": "Shared fact", "scope": "site"}).insert()

	def test_uploaded_original_is_private_until_selected_as_page_content(self):
		buffer = io.BytesIO()
		Image.new("RGB", (4, 4), "blue").save(buffer, "PNG")
		content = buffer.getvalue()
		url = api.save_attached_image("data:image/png;base64," + base64.b64encode(content).decode())
		asset = {
			"id": f"upload:{url}",
			"url": url,
			"original_url": url,
			"provider": "Upload",
			"role": "reference",
			"selected": True,
			"preview_only": True,
		}
		DesignBrief(self.page.name).remember_assets([asset])
		with self.assertRaisesRegex(ValueError, "Mark the upload"):
			workspace.prepare_upload(self.page.name, asset["id"])
		with self.assertRaisesRegex(ValueError, "not ready"):
			validate_asset_usage([asset], {"src": url})
		workspace.classify_asset(self.page.name, asset["id"], "product")
		state = workspace.prepare_upload(self.page.name, asset["id"])
		self.assertTrue(state["assets"][0]["url"].startswith("/files/"))
		public = frappe.get_doc("File", {"file_url": state["assets"][0]["url"]})
		self.assertEqual(public.get_content(), content)
		self.assertFalse(state["assets"][0]["preview_only"])
		self.assertEqual(state["assets"][0]["original_url"], url)

	def test_plugin_activation_requires_verified_exact_candidate_and_is_idempotent(self):
		candidate, value = bob.stage_plugin(
			self.page.name,
			{
				"name": f"bob-fixture-{frappe.generate_hash(length=8)}",
				"label": "Fixture",
				"description": "Regression fixture for staged activation",
				"code": "export default { install() {} }",
			},
		)
		payload = {"page_id": self.page.name, "candidate_id": candidate.name}
		with patch.object(
			bob, "save_plugin", return_value=SimpleNamespace(label="Fixture", version=value["version"])
		) as save:
			with self.assertRaisesRegex(ValueError, "not passed"):
				bob.activate_candidate(payload)
			bob.report_load(
				value["token"],
				{"registered": [{"surface": "toolbarItems", "name": "fixture"}]},
				candidate.name,
				self.page.name,
			)
			self.assertIn("Installed", bob.activate_candidate(payload))
			self.assertIn("already installed", bob.activate_candidate(payload))
			save.assert_called_once()
