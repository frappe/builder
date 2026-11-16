import sys
from contextlib import contextmanager
from importlib import import_module
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import get_decrypted_password

import builder.ai
import builder.builder.patches
from builder.ai.models import DEFAULT_AI_MODEL, GatewayListing, ModelRegistry
from builder.ai.presets import ADOPTED_DEFAULT_KEY, match_model, sync_site_provider

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
		with fresh_import_without_litellm(
			"builder.builder.patches.upgrade_ai_models", "builder.ai.presets", "builder.ai.llm"
		):
			import_module("builder.builder.patches.upgrade_ai_models")

	def test_the_ai_api_loads_without_litellm(self):
		# the first Billing or Bob call in a web worker must not wait for litellm to import
		with fresh_import_without_litellm("builder.ai.api", "builder.ai.llm"):
			import_module("builder.ai.api")


@contextmanager
def fresh_import_without_litellm(*modules: str):
	"""Re-import `modules` with litellm missing, then put the originals back. A re-import
	also rebinds the parent packages' attributes, which later patch() targets go through."""
	with (
		patch.dict(sys.modules, {"litellm": None}),
		patch.dict(vars(builder.ai)),
		patch.dict(vars(builder.builder.patches)),
	):
		for module in modules:
			sys.modules.pop(module, None)
		yield


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
		self.assertEqual((provider.name, provider.enabled), ("Frappe", 1))
		with site_config(SITE_KEY):
			self.assertEqual(provider.base_url(), GATEWAY_BASE)

	def test_the_row_never_holds_the_gateway_address(self):
		# members can read the row; the address is the host's
		provider = self.sync(SITE_KEY)
		self.assertIsNone(provider.api_base)
		modified = provider.modified
		self.assertEqual(self.sync(SITE_KEY).modified, modified)  # nothing left to put back

	def test_the_key_is_read_from_site_config_and_never_stored(self):
		provider = self.sync(SITE_KEY)
		with site_config(SITE_KEY):
			self.assertEqual(provider.resolved_key(), "grove-key")
		stored = get_decrypted_password("Builder AI Provider", "Frappe", "api_key", raise_exception=False)
		self.assertIsNone(stored)

	def test_a_new_gateway_url_follows_site_config(self):
		self.sync(SITE_KEY)
		moved = {"ai_keys": [{"gateway_url": "https://moved.test", "api_key": "grove-key"}]}
		provider = self.sync(moved)
		with site_config(moved):
			self.assertEqual(provider.base_url(), "https://moved.test/openai/v1")

	def test_the_balance_is_read_from_the_gateway_host(self):
		provider = self.sync(SITE_KEY)
		with site_config(SITE_KEY):
			self.assertEqual(provider.credits_url, "https://grove.test/v1/key/balance")

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

	def test_registering_the_provider_makes_the_gateway_model_the_default(self):
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		with (
			patch(
				"builder.ai.models.fetch_listing", return_value=["openai/gpt-5.6-terra", "openai/gpt-6-luna"]
			),
			patch("frappe.get_hooks", return_value=[]),
		):
			self.sync(SITE_KEY)
		self.assertEqual(default_model(), DEFAULT_AI_MODEL)

	def test_a_default_the_site_picked_stays(self):
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "frappe/openai/gpt-6-luna")
		with patch(
			"builder.ai.models.fetch_listing", return_value=["openai/gpt-5.6-terra", "openai/gpt-6-luna"]
		):
			self.sync(SITE_KEY)
		self.assertEqual(default_model(), "frappe/openai/gpt-6-luna")

	def test_a_gateway_that_is_down_sets_no_default(self):
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		with patch("builder.ai.models.fetch_listing", return_value=OSError("down")):
			self.sync(SITE_KEY)
		self.assertFalse(default_model())

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
			patch("builder.ai.site_key.allowance", return_value=None),
		):
			self.assertEqual(get_site_ai_credits(), {"balance": 4.5, "spent": 0.5})
		self.assertEqual(get.call_args.args[0], "https://grove.test/v1/key/balance")
		self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer grove-key"})

	def test_a_host_that_meters_the_key_keeps_its_balance_to_itself(self):
		from builder.ai.api import get_site_ai_credits

		with (
			site_config(SITE_KEY),
			patch("builder.ai.models.requests.get") as get,
			patch("builder.ai.site_key.allowance", return_value=Mock()),
		):
			self.assertIsNone(get_site_ai_credits())
		get.assert_not_called()


MEMBER = "builder-ai-member@example.com"


class TestSiteProviderIsLocked(FrappeTestCase):
	"""Site config owns the Frappe provider: a member (or a script) can't change, switch off, remove or
	impersonate it, and an edited row still sends the key only to the gateway site config names."""

	def setUp(self):
		TestSiteProvider.setUp(self)
		with (
			site_config(SITE_KEY),
			patch("builder.ai.models.fetch_listing", return_value=["openai/gpt-6-luna"]),
		):
			sync_site_provider()
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(ModelRegistry.clear_cache)
		if not frappe.db.exists("User", MEMBER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": MEMBER,
					"first_name": "Member",
					"send_welcome_email": 0,
					"roles": [{"role": "Website Manager"}],
				}
			).insert(ignore_permissions=True)

	def as_member(self, call, *args, **kwargs):
		frappe.set_user(MEMBER)
		try:
			with site_config(SITE_KEY), self.assertRaises(frappe.PermissionError):
				call(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def test_a_member_cannot_switch_it_off_edit_or_remove_it(self):
		from frappe.client import set_value

		from builder.ai.api import delete_ai_provider, save_ai_provider

		self.as_member(save_ai_provider, {"enabled": 0}, name="Frappe")
		self.as_member(save_ai_provider, {"api_key": "member-key"}, name="Frappe")
		self.as_member(set_value, "Builder AI Provider", "Frappe", "api_base", "https://evil.test/v1")
		self.as_member(delete_ai_provider, "Frappe")
		self.as_member(frappe.rename_doc, "Builder AI Provider", "Frappe", "Mine")
		provider = frappe.get_doc("Builder AI Provider", "Frappe")
		self.assertEqual((provider.enabled, provider.api_base), (1, None))
		self.assertTrue(frappe.db.exists("Builder AI Model", "frappe/openai/gpt-6-luna"))

	def test_no_other_row_can_claim_the_site_key(self):
		from frappe.client import insert, set_value

		new = {"doctype": "Builder AI Provider", "provider_name": "Evil", "api_base": "https://evil.test/v1"}
		self.as_member(insert, {**new, "from_site_config": 1})
		frappe.set_user(MEMBER)
		insert(new)
		frappe.set_user("Administrator")
		self.as_member(set_value, "Builder AI Provider", "Evil", "from_site_config", 1)

	def test_a_member_can_still_connect_a_provider_of_their_own(self):
		from builder.ai.api import save_ai_provider

		frappe.set_user(MEMBER)
		name = save_ai_provider({"provider_name": "Mine", "api_base": "https://mine.test/v1", "api_key": "k"})
		self.assertEqual(name, "Mine")

	def test_a_script_cannot_change_it_even_as_administrator(self):
		from frappe.utils.safe_exec import safe_exec

		for script in (
			'doc = frappe.get_doc("Builder AI Provider", "Frappe")\ndoc.enabled = 0\ndoc.save()',
			'frappe.delete_doc("Builder AI Provider", "Frappe", force=True)',
		):
			with site_config(SITE_KEY), self.assertRaises(frappe.PermissionError):
				safe_exec(script)
		self.assertEqual(frappe.db.get_value("Builder AI Provider", "Frappe", "enabled"), 1)

	def test_an_edited_row_still_sends_the_key_only_to_the_configured_gateway(self):
		from builder.ai.llm import route
		from builder.ai.presets import preset_for

		# what a script that skips validation could do to the row
		frappe.db.set_value(
			"Builder AI Provider",
			"Frappe",
			{"api_base": "https://evil.test/v1", "litellm_provider": "anthropic"},
		)
		ModelRegistry.clear_cache()
		provider = frappe.get_doc("Builder AI Provider", "Frappe")
		with site_config(SITE_KEY):
			model, overrides, key = route("frappe/openai/gpt-6-luna", None)
			self.assertEqual(
				(model, overrides, key), ("openai/openai/gpt-6-luna", {"api_base": GATEWAY_BASE}, "grove-key")
			)
			self.assertTrue(GatewayListing(provider).request()[0].startswith(GATEWAY_BASE))
			self.assertEqual(provider.credits_url, "https://grove.test/v1/key/balance")
			provider.api_base, provider.litellm_provider = None, "openrouter"
			self.assertIsNone(preset_for(provider))

	def test_a_sync_puts_an_edited_row_back(self):
		frappe.db.set_value(
			"Builder AI Provider",
			"Frappe",
			{"api_base": "https://evil.test/v1", "litellm_provider": "anthropic", "enabled": 0},
		)
		with site_config(SITE_KEY):
			sync_site_provider()
		provider = frappe.get_doc("Builder AI Provider", "Frappe")
		self.assertEqual(
			(provider.api_base, provider.litellm_provider, provider.enabled), (None, "openai", 1)
		)


class TestDefaultModel(FrappeTestCase):
	"""The gateway model a host prefers becomes the default, unless the site picked one of its own."""

	LISTED = ("openai/gpt-6.1-sol-mini", "openai/gpt-6.1-sol", "openai/gpt-6.1-luna")

	def setUp(self):
		TestSiteProvider.setUp(self)
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		frappe.db.set_default(ADOPTED_DEFAULT_KEY, "")
		self.addCleanup(ModelRegistry.clear_cache)

	def sync(self, wanted="sol", listed=LISTED):
		with (
			site_config(SITE_KEY),
			patch("builder.ai.models.fetch_listing", return_value=list(listed)),
			patch("builder.ai.presets.preferred_model", return_value=wanted),
		):
			sync_site_provider()
			GatewayListing(frappe.get_doc("Builder AI Provider", "Frappe")).sync()

	def test_the_host_preference_names_the_default(self):
		self.sync()
		self.assertEqual(default_model(), "frappe/openai/gpt-6.1-sol")

	def test_the_site_own_pick_stays(self):
		self.sync()
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "frappe/openai/gpt-6.1-luna")
		self.sync()
		self.assertEqual(default_model(), "frappe/openai/gpt-6.1-luna")

	def test_a_default_set_by_the_sync_follows_a_new_preference(self):
		self.sync()
		self.sync(wanted="luna")
		self.assertEqual(default_model(), "frappe/openai/gpt-6.1-luna")

	def test_a_default_nobody_can_call_gives_way(self):
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "frappe/openai/gone")
		self.sync()
		self.assertEqual(default_model(), "frappe/openai/gpt-6.1-sol")

	def test_a_model_switched_off_is_not_made_the_default(self):
		self.sync(listed=("openai/gpt-6.1-luna",))
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		frappe.get_doc(
			{
				"doctype": "Builder AI Model",
				"provider": "Frappe",
				"model_id": "openai/gpt-6.1-sol",
				"enabled": 0,
			}
		).insert(ignore_permissions=True)
		self.sync()
		self.assertFalse(default_model())

	def test_a_gateway_without_the_model_changes_nothing(self):
		self.sync(listed=("openai/gpt-6.1-luna",))
		self.assertFalse(default_model())

	def test_the_match(self):
		self.assertEqual(match_model("sol", list(self.LISTED)), "openai/gpt-6.1-sol")
		self.assertEqual(match_model("GPT-6.1-SOL-MINI", list(self.LISTED)), "openai/gpt-6.1-sol-mini")
		self.assertEqual(match_model("openai/gpt-6.1-luna", list(self.LISTED)), "openai/gpt-6.1-luna")
		self.assertIsNone(match_model("terra", list(self.LISTED)))
		self.assertIsNone(match_model("", list(self.LISTED)))


def default_model() -> str | None:
	return frappe.db.get_single_value("Builder Settings", "default_ai_model")
