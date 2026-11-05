import sys
from importlib import import_module
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import get_decrypted_password

from builder.ai.models import DEFAULT_AI_MODEL
from builder.ai.presets import sync_site_provider

GATEWAY = "https://grove.test"
GATEWAY_BASE = "https://grove.test/openai/v1"
SITE_KEY = {"ai_keys": [{"gateway_url": GATEWAY, "api_key": "grove-key"}]}


class TestMigrateWithoutLitellm(FrappeTestCase):
	def test_the_model_upgrade_patch_loads_when_litellm_cannot(self):
		with patch.dict(sys.modules, {"litellm": None}):
			for module in (
				"builder.builder.patches.upgrade_ai_models",
				"builder.ai.presets",
				"builder.ai.llm",
			):
				sys.modules.pop(module, None)
			import_module("builder.builder.patches.upgrade_ai_models")


class TestSiteProvider(FrappeTestCase):
	def setUp(self):
		# a site with a real key already has the row: the class rollback brings it back
		names = frappe.get_all("Builder AI Provider", filters={"from_site_config": 1}, pluck="name")
		frappe.db.delete("Builder AI Model", {"provider": ["in", names or [""]]})
		for name in names:
			frappe.delete_doc("Builder AI Provider", name, force=True, ignore_permissions=True)

	def sync(self, conf: dict):
		with patch.dict(frappe.local.conf, conf):
			sync_site_provider()
			return frappe.get_doc("Builder AI Provider", {"from_site_config": 1})

	def test_a_site_config_key_connects_the_frappe_provider(self):
		provider = self.sync(SITE_KEY)
		self.assertEqual((provider.name, provider.api_base, provider.enabled), ("Frappe", GATEWAY_BASE, 1))

	def test_the_key_is_read_from_site_config_and_never_stored(self):
		provider = self.sync(SITE_KEY)
		with patch.dict(frappe.local.conf, SITE_KEY):
			self.assertEqual(provider.resolved_key(), "grove-key")
		stored = get_decrypted_password("Builder AI Provider", "Frappe", "api_key", raise_exception=False)
		self.assertIsNone(stored)

	def test_a_new_gateway_url_follows_site_config(self):
		self.sync(SITE_KEY)
		moved = {"ai_keys": [{"gateway_url": "https://moved.test", "api_key": "grove-key"}]}
		self.assertEqual(self.sync(moved).api_base, "https://moved.test/openai/v1")

	def test_the_balance_is_read_from_the_gateway_host(self):
		self.assertEqual(self.sync(SITE_KEY).credits_url, "https://grove.test/v1/credits")

	def test_removing_the_key_turns_the_provider_off(self):
		self.sync(SITE_KEY)
		provider = self.sync({"ai_keys": []})
		self.assertEqual(provider.enabled, 0)
		with patch.dict(frappe.local.conf, {"ai_keys": []}):
			self.assertIsNone(provider.resolved_key())

	def test_a_site_config_key_counts_as_configured(self):
		from builder.ai.api import ai_setup_state

		self.sync(SITE_KEY)
		frappe.get_doc(
			{
				"doctype": "Builder AI Model",
				"provider": "Frappe",
				"model_id": "openai/gpt-6-luna",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		with (
			patch.dict(frappe.local.conf, SITE_KEY),
			patch("builder.ai.api.settings_api_key", return_value=None),
		):
			self.assertTrue(ai_setup_state()["configured"])

	def test_install_and_migrate_connect_the_provider(self):
		from builder.install import after_install, after_migrate

		for hook in (after_install, after_migrate):
			self.setUp()
			with (
				patch.dict(frappe.local.conf, SITE_KEY),
				patch("builder.install.create_new_folder"),
				patch("builder.install.sync_page_templates"),
				patch("builder.install.sync_block_templates"),
				patch("builder.install.sync_builder_tokens"),
				patch("builder.install.add_composite_index_to_web_page_view"),
				patch("builder.install.sync_standard_builder_pages"),
			):
				hook()
			self.assertEqual(frappe.db.get_value("Builder AI Provider", {"from_site_config": 1}), "Frappe")

	def test_a_new_provider_sets_the_default_model_only_when_none_is_set(self):
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		self.sync(SITE_KEY)
		self.assertEqual(frappe.db.get_single_value("Builder Settings", "default_ai_model"), DEFAULT_AI_MODEL)

		self.setUp()
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "frappe/openai/chosen")
		self.sync(SITE_KEY)
		self.assertEqual(
			frappe.db.get_single_value("Builder Settings", "default_ai_model"), "frappe/openai/chosen"
		)

	def test_an_entry_without_a_key_connects_nothing(self):
		with patch.dict(frappe.local.conf, {"ai_keys": [{"gateway_url": GATEWAY}]}):
			sync_site_provider()
		self.assertFalse(frappe.db.exists("Builder AI Provider", {"from_site_config": 1}))
