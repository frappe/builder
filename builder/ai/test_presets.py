import sys
from contextlib import contextmanager
from importlib import import_module
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import get_decrypted_password

from builder.ai.models import DEFAULT_AI_MODEL
from builder.ai.presets import sync_site_provider

GATEWAY = "https://grove.test"
GATEWAY_BASE = "https://grove.test/openai/v1"
SITE_KEY = {"ai_keys": [{"gateway_url": GATEWAY, "api_key": "grove-key"}]}
NO_KEY = {"ai_keys": []}


@contextmanager
def site_config(cached: dict, files: dict | None = None):
	"""`cached` is the config a request sees, `files` what the config files hold now."""
	files = cached if files is None else files
	with (
		patch.dict(frappe.local.conf, cached),
		patch("frappe.get_site_config", return_value=frappe._dict(files)) as read_files,
	):
		yield read_files


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

	def sync(self, cached: dict, files: dict | None = None):
		with site_config(cached, files):
			sync_site_provider()
			return frappe.get_doc("Builder AI Provider", {"from_site_config": 1})

	def test_a_site_config_key_connects_the_frappe_provider(self):
		provider = self.sync(SITE_KEY)
		self.assertEqual((provider.name, provider.api_base, provider.enabled), ("Frappe", GATEWAY_BASE, 1))

	def test_the_key_is_read_from_site_config_and_never_stored(self):
		provider = self.sync(SITE_KEY)
		with site_config(SITE_KEY):
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
		provider = self.sync(NO_KEY)
		self.assertEqual(provider.enabled, 0)
		with site_config(NO_KEY):
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
			site_config(SITE_KEY),
			patch("builder.ai.api.settings_api_key", return_value=None),
		):
			self.assertTrue(ai_setup_state()["configured"])

	def test_registering_the_provider_sets_the_default_model_only_when_none_is_set(self):
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		self.sync(SITE_KEY)
		self.assertEqual(frappe.db.get_single_value("Builder Settings", "default_ai_model"), DEFAULT_AI_MODEL)

		self.setUp()
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "frappe/openai/chosen")
		self.sync(SITE_KEY)
		self.assertEqual(
			frappe.db.get_single_value("Builder Settings", "default_ai_model"), "frappe/openai/chosen"
		)

	def test_registering_the_provider_lists_its_models(self):
		with patch("builder.ai.models.fetch_listing", return_value=["openai/gpt-6-luna"]):
			self.sync(SITE_KEY)
		self.assertTrue(frappe.db.exists("Builder AI Model", "frappe/openai/gpt-6-luna"))

	def test_a_gateway_that_is_down_does_not_stop_the_registration(self):
		with patch("builder.ai.models.fetch_listing", return_value=OSError("down")):
			provider = self.sync(SITE_KEY)
		self.assertEqual(provider.enabled, 1)

	def test_an_entry_without_a_key_connects_nothing(self):
		with site_config({"ai_keys": [{"gateway_url": GATEWAY}]}):
			sync_site_provider()
		self.assertFalse(frappe.db.exists("Builder AI Provider", {"from_site_config": 1}))

	def test_the_key_is_read_from_the_files_while_the_cache_misses_it(self):
		provider = self.sync(NO_KEY, files=SITE_KEY)
		with site_config(NO_KEY, files=SITE_KEY):
			self.assertEqual(provider.resolved_key(), "grove-key")

	def test_the_setup_state_connects_a_key_added_after_the_config_was_cached(self):
		from builder.ai.api import ai_setup_state

		with (
			site_config(NO_KEY, files=SITE_KEY),
			patch("builder.ai.models.fetch_listing", return_value=["openai/gpt-6-luna"]),
			patch("builder.ai.api.settings_api_key", return_value=None),
		):
			self.assertTrue(ai_setup_state()["configured"])


class TestSiteAICredits(FrappeTestCase):
	def test_the_balance_is_read_with_the_site_config_key(self):
		from builder.ai.api import get_site_ai_credits

		response = Mock(json=Mock(return_value={"balance": 4.5, "spent": 0.5}))
		with (
			site_config(NO_KEY, files=SITE_KEY),
			patch("builder.ai.models.requests.get", return_value=response) as get,
		):
			self.assertEqual(get_site_ai_credits(), {"balance": 4.5, "spent": 0.5})
		self.assertEqual(get.call_args.args[0], "https://grove.test/v1/credits")
		self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer grove-key"})
