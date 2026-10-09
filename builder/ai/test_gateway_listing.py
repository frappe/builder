from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.models import GatewayListing, ModelRegistry

PROVIDER = "Test Gateway"


def listing(*ids):
	response = MagicMock()
	response.json.return_value = {"data": [{"id": i} for i in ids]}
	return response


class TestGatewayListing(FrappeTestCase):
	def setUp(self):
		self.provider = frappe.get_doc(
			{
				"doctype": "Builder AI Provider",
				"provider_name": PROVIDER,
				"api_base": "https://gw.test/v1",
				"api_key": "gw-key",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.delete("Builder AI Model", {"provider": PROVIDER})
		frappe.delete_doc("Builder AI Provider", PROVIDER, force=True, ignore_permissions=True)
		frappe.cache.delete_value(GatewayListing.cache_key(PROVIDER))
		ModelRegistry.clear_cache()

	def sync(self, *ids):
		with patch("builder.ai.models.requests.get", return_value=listing(*ids)) as get:
			result = GatewayListing(self.provider).sync()
		return result, get

	def served_names(self):
		with patch("builder.ai.models.fetch_openrouter_catalog", return_value={}):
			return {m["name"] for group in ModelRegistry.available() for m in group["models"]}

	def test_adds_a_row_per_listed_chat_model(self):
		result, _ = self.sync("vendor/chat-a", "vendor/text-embedding-3")
		self.assertEqual(result["added"], ["vendor/chat-a"])
		self.assertEqual(result["skipped"], ["vendor/text-embedding-3"])
		self.assertTrue(frappe.db.exists("Builder AI Model", "test-gateway/vendor/chat-a"))

	def test_leaves_a_switched_off_model_off(self):
		self.sync("vendor/chat-a")
		frappe.db.set_value("Builder AI Model", "test-gateway/vendor/chat-a", "enabled", 0)
		result, _ = self.sync("vendor/chat-a")
		self.assertEqual(result["added"], [])
		self.assertEqual(frappe.db.get_value("Builder AI Model", "test-gateway/vendor/chat-a", "enabled"), 0)

	def test_hides_a_model_the_gateway_stopped_listing(self):
		self.sync("vendor/chat-a", "vendor/chat-b")
		self.sync("vendor/chat-a")
		self.assertIn("test-gateway/vendor/chat-a", self.served_names())
		self.assertNotIn("test-gateway/vendor/chat-b", self.served_names())

	def test_an_unreachable_gateway_hides_nothing(self):
		self.sync("vendor/chat-a")
		with patch("builder.ai.models.requests.get", side_effect=ConnectionError("down")):
			with self.assertRaises(ConnectionError):
				GatewayListing(self.provider).sync()
		self.assertIn("test-gateway/vendor/chat-a", self.served_names())

	def test_asks_an_openai_gateway_with_a_bearer_key(self):
		_, get = self.sync()
		self.assertEqual(get.call_args.args[0], "https://gw.test/v1/models")
		self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer gw-key"})

	def test_asks_an_anthropic_gateway_its_own_way(self):
		self.provider.db_set({"api_base": "https://gw.test/anthropic", "litellm_provider": "anthropic"})
		_, get = self.sync()
		self.assertEqual(get.call_args.args[0], "https://gw.test/anthropic/v1/models")
		self.assertEqual(get.call_args.kwargs["headers"]["x-api-key"], "gw-key")
