"""Model discovery: the frontier policy, keeping a provider's rows on it, and connecting."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.discovery import Discovery, frontier, load_policy
from builder.ai.listings import ListingError
from builder.ai.presets import connect

PROVIDER = "Test Discovery"
PREFIX = "test-discovery"
PRESET = {
	"id": "anthropic",
	"name": PROVIDER,
	"route_prefix": PREFIX,
	"litellm_provider": "anthropic",
	"listing": "anthropic",
	"catalog": "anthropic",
	"lab": "anthropic",
}


def model(released: str, family: str = "", **facts) -> dict:
	return {
		"label": family or "Model",
		"family": family,
		"released": released,
		"tools": True,
		"input": ["text", "image"],
		"output": ["text"],
		"context": 200_000,
		**facts,
	}


class TestFrontier(FrappeTestCase):
	def pick(self, described: dict, lab: str = "anthropic") -> list[str]:
		candidates = [{**facts, "id": model_id, "lab": lab} for model_id, facts in described.items()]
		return [c["id"] for c in frontier(candidates, load_policy())]

	def test_keeps_the_newest_of_each_family(self):
		picked = self.pick(
			{
				"claude-sonnet-5": model("2026-06-29", "claude-sonnet"),
				"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet"),
			}
		)
		self.assertEqual(picked, ["claude-sonnet-5-5"])

	def test_drops_what_cannot_do_agentic_design_work(self):
		picked = self.pick(
			{
				"claude-opus-5-5": model("2026-09-22", "claude-opus"),
				"claude-haiku-5-5": model("2026-10-07", "claude-haiku"),
				"no-tools": model("2026-09-01", "a", tools=False),
				"text-only": model("2026-09-01", "b", input=["text"]),
				"short-context": model("2026-09-01", "c", context=32_000),
			}
		)
		self.assertEqual(picked, ["claude-opus-5-5"])

	def test_drops_what_the_newest_has_left_far_behind(self):
		picked = self.pick(
			{
				"claude-opus-5-5": model("2026-09-22", "claude-opus"),
				"claude-fable-4": model("2026-03-01", "claude-fable"),
			}
		)
		self.assertEqual(picked, ["claude-opus-5-5"])

	def test_caps_each_lab_and_puts_labs_in_policy_order(self):
		candidates = [
			{**model("2026-10-01", f"gpt-{n}"), "id": f"gpt-{n}", "lab": "openai"} for n in range(4)
		] + [{**model("2026-09-01", "claude-opus"), "id": "claude-opus-5-5", "lab": "anthropic"}]
		picked = [c["id"] for c in frontier(candidates, load_policy())]
		self.assertEqual(picked[0], "claude-opus-5-5")
		self.assertEqual(len([p for p in picked if p.startswith("gpt-")]), 3)

	def test_a_lab_outside_the_policy_is_left_out(self):
		self.assertEqual(self.pick({"kimi-k3": model("2026-10-01", "kimi")}, lab="moonshotai"), [])


class TestDiscoverySync(FrappeTestCase):
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

	def tearDown(self):
		frappe.db.delete("Builder AI Model", {"provider": PROVIDER})
		frappe.delete_doc("Builder AI Provider", PROVIDER, force=True, ignore_permissions=True)
		frappe.cache.delete_value(Discovery(self.provider).cache_key())

	def sync(self, described: dict) -> list[str]:
		listed = {model_id: {} for model_id in described}
		with patch("builder.ai.discovery.described_models", return_value={"anthropic": described}):
			return Discovery(self.provider).sync(listed)

	def row(self, model_id: str):
		return frappe.db.get_value(
			"Builder AI Model",
			f"{PREFIX}/{model_id}",
			["enabled", "discovered", "frontier_rank"],
			as_dict=True,
		)

	def test_adds_the_frontier_and_retires_what_it_replaced(self):
		self.sync({"claude-sonnet-5": model("2026-06-29", "claude-sonnet")})
		self.sync(
			{
				"claude-sonnet-5": model("2026-06-29", "claude-sonnet"),
				"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet"),
			}
		)
		self.assertEqual(
			(self.row("claude-sonnet-5-5").enabled, self.row("claude-sonnet-5-5").discovered), (1, 1)
		)
		self.assertEqual(self.row("claude-sonnet-5").enabled, 0)

	def test_ranks_rows_best_first(self):
		names = self.sync(
			{
				"claude-opus-5-5": model("2026-09-22", "claude-opus"),
				"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet"),
			}
		)
		self.assertEqual(names, [f"{PREFIX}/claude-sonnet-5-5", f"{PREFIX}/claude-opus-5-5"])
		self.assertEqual(self.row("claude-opus-5-5").frontier_rank, 2)

	def test_a_model_switched_back_on_by_hand_stays_on(self):
		self.sync({"claude-sonnet-5": model("2026-06-29", "claude-sonnet")})
		newer = {
			"claude-sonnet-5": model("2026-06-29", "claude-sonnet"),
			"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet"),
		}
		self.sync(newer)
		doc = frappe.get_doc("Builder AI Model", f"{PREFIX}/claude-sonnet-5")
		doc.enabled = 1
		doc.save(ignore_permissions=True)
		self.sync(newer)
		self.assertEqual(
			(self.row("claude-sonnet-5").enabled, self.row("claude-sonnet-5").discovered), (1, 0)
		)

	def test_a_row_added_by_hand_is_never_retired(self):
		frappe.get_doc(
			{"doctype": "Builder AI Model", "provider": PROVIDER, "model_id": "claude-custom", "enabled": 1}
		).insert(ignore_permissions=True)
		self.sync({"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet")})
		self.assertEqual(self.row("claude-custom").enabled, 1)

	def test_an_empty_frontier_leaves_the_rows_alone(self):
		self.sync({"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet")})
		self.assertEqual(self.sync({"claude-haiku-5-5": model("2026-10-07", "claude-haiku")}), [])
		self.assertEqual(self.row("claude-sonnet-5-5").enabled, 1)


class TestConnect(FrappeTestCase):
	def tearDown(self):
		frappe.db.delete("Builder AI Model", {"provider": PROVIDER})
		frappe.delete_doc(
			"Builder AI Provider", PROVIDER, force=True, ignore_permissions=True, ignore_missing=True
		)

	def test_a_rejected_key_is_never_saved(self):
		rejected = ListingError('401: {"error": {"type": "authentication_error"}}')
		with patch("builder.ai.listings.list_models", side_effect=rejected):
			with self.assertRaises(frappe.ValidationError):
				connect(PRESET, "sk-ant-bad")
		self.assertFalse(frappe.db.exists("Builder AI Provider", PROVIDER))

	def test_connecting_returns_the_models_on_offer_best_first(self):
		described = {
			"claude-opus-5-5": model("2026-09-22", "claude-opus", label="Claude Opus 5.5"),
			"claude-sonnet-5-5": model("2026-09-28", "claude-sonnet", label="Claude Sonnet 5.5"),
		}
		with (
			patch("builder.ai.listings.list_models", return_value={i: {} for i in described}),
			patch("builder.ai.discovery.described_models", return_value={"anthropic": described}),
		):
			result = connect(PRESET, "sk-ant-good")
		self.assertEqual(result["provider"], PROVIDER)
		self.assertEqual([m["label"] for m in result["models"]], ["Claude Sonnet 5.5", "Claude Opus 5.5"])
