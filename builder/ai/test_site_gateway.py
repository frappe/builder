"""The gateway site config names is the host's: members never read its address, and asking for the
latest models sends the host's key to it only so often."""

import json
import traceback
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import api, test_presets
from builder.ai.models import SITE_KEY_LISTING_KEY
from builder.ai.test_presets import MEMBER, SITE_KEY, site_config

HOST = "grove.test"
LISTED = ["openai/gpt-6-luna"]


class TestSiteGateway(FrappeTestCase):
	def setUp(self):
		test_presets.TestSiteProviderIsLocked.setUp(self)
		frappe.cache.delete(frappe.cache.make_key(SITE_KEY_LISTING_KEY))
		self.addCleanup(frappe.cache.delete, frappe.cache.make_key(SITE_KEY_LISTING_KEY))
		self.enterContext(site_config(SITE_KEY))
		self.enterContext(patch("frappe.enqueue"))
		self.enterContext(patch("builder.ai.models.fetch_openrouter_catalog", return_value={}))

	def test_members_read_no_gateway_address(self):
		frappe.set_user(MEMBER)
		models = api.get_ai_models()
		providers = frappe.get_list("Builder AI Provider", fields=["*"])
		row = frappe.get_doc("Builder AI Provider", "Frappe").as_dict()
		self.assertNotIn(HOST, json.dumps([models, providers, row], default=str))
		[frappe_models] = [g["models"] for g in models if g["provider"] == "Frappe"]
		# the picker still knows it is a gateway that may report credits
		self.assertTrue(all(m["gateway"] for m in frappe_models))

	def test_asking_for_the_latest_models_lists_the_gateway_at_most_once_a_minute(self):
		frappe.set_user(MEMBER)
		with patch("builder.ai.models.fetch_listing", return_value=LISTED) as fetch:
			api.sync_ai_models("Frappe")
			api.sync_ai_models("Frappe")
			api.sync_ai_models()
			api.import_provider_models("Frappe")
			api.get_addable_models("Frappe")
		asked = [c for c in fetch.call_args_list if HOST in c.args[0][0]]
		self.assertEqual(len(asked), 1)

	def test_another_gateway_is_still_listed_whenever_asked(self):
		mine = frappe.get_doc(
			{"doctype": "Builder AI Provider", "provider_name": "Mine", "api_base": "https://mine.test/v1"}
		).insert(ignore_permissions=True)
		with patch("builder.ai.models.fetch_listing", return_value=LISTED) as fetch:
			api.sync_ai_models(mine.name)
			api.sync_ai_models(mine.name)
		self.assertEqual(fetch.call_count, 2)

	def test_a_gateway_that_fails_is_named_not_addressed(self):
		# as requests raises it: urllib3's error, naming the host, inside its args
		failure = ConnectionError(RuntimeError(f"HTTPSConnectionPool(host='{HOST}', port=443): Max retries"))
		with (
			patch("builder.ai.models.fetch_listing", return_value=failure),
			self.assertRaises(frappe.ValidationError) as raised,
		):
			api.import_provider_models("Frappe")
		self.assertIn("Could not reach Frappe", str(raised.exception))
		# a member can be shown the traceback, which carries the error it was raised from
		self.assertNotIn(HOST, "".join(traceback.format_exception(raised.exception)))
