"""Adding a model by hand: past the frontier, and kept off discovery's books."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.catalog import ProviderCatalog
from builder.ai.discovery import Discovery
from builder.ai.test_discovery import model

PROVIDER = "Test Catalog"
PREFIX = "test-catalog"
DESCRIBED = {
	"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet"),
	"claude-sonnet-5": model("2026-06-29", "claude-sonnet"),
	"claude-no-tools": model("2026-10-01", "claude-x", tools=False),
}


class TestAddByHand(FrappeTestCase):
	def setUp(self):
		self.provider = frappe.get_doc(
			{
				"doctype": "Builder AI Provider",
				"provider_name": PROVIDER,
				"route_prefix": PREFIX,
				"litellm_provider": "anthropic",
				"api_key": "sk-ant-test",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		self.patches = [
			patch("builder.ai.catalog.list_models", return_value={i: {} for i in DESCRIBED}),
			patch("builder.ai.discovery.described_models", return_value={"anthropic": DESCRIBED}),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in self.patches:
			p.stop()
		frappe.db.delete("Builder AI Model", {"provider": PROVIDER})
		frappe.delete_doc("Builder AI Provider", PROVIDER, force=True, ignore_permissions=True)
		frappe.cache.delete_value(Discovery(self.provider).cache_key())

	def row(self, model_id: str):
		return frappe.db.get_value(
			"Builder AI Model", f"{PREFIX}/{model_id}", ["enabled", "discovered"], as_dict=True
		)

	def test_offers_what_the_picker_leaves_out_and_can_call_tools(self):
		Discovery(self.provider).sync({i: {} for i in DESCRIBED})
		offered = [m["id"] for m in ProviderCatalog(self.provider).offered()]
		self.assertEqual(offered, ["claude-sonnet-5"])

	def test_a_model_the_provider_does_not_serve_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			ProviderCatalog(self.provider).add("claude-imaginary")

	def test_a_model_added_by_hand_outlives_the_next_sync(self):
		Discovery(self.provider).sync({i: {} for i in DESCRIBED})
		ProviderCatalog(self.provider).add("claude-sonnet-5")
		Discovery(self.provider).sync({i: {} for i in DESCRIBED})
		self.assertEqual(
			(self.row("claude-sonnet-5").enabled, self.row("claude-sonnet-5").discovered), (1, 0)
		)
