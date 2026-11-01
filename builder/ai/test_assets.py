"""Offline stock contracts; no site initialization, real keys or provider requests.

Run: <bench>/env/bin/python -m unittest builder.ai.test_assets
"""

import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
import requests

from builder.ai.agent.tools import images
from builder.ai.assets import MAX_RESULTS, MagnificStock

STOCK_RESOURCE = {
	"id": 15667327,
	"title": "White t-shirt with copy space on gray background",
	"url": "https://www.freepik.com/free-photo/white-t-shirts-with-copy-space-gray-background_15667327.htm",
	"author": {"name": "John Doe"},
	"licenses": [{"type": "premium", "url": "https://www.freepik.com/profile/license/pdf/15667327"}],
	"image": {
		"type": "photo",
		"orientation": "horizontal",
		"source": {
			"size": "740x640",
			"key": "large",
			"url": "https://img.freepik.com/free-photo/tshirt_53876-104920.jpg",
		},
	},
}
UNSPLASH_PHOTO = {
	"id": "photo_A-1",
	"alt_description": "Coastal landscape",
	"width": 4000,
	"height": 3000,
	"urls": {
		"regular": "https://images.unsplash.com/photo-1?w=1080&ixid=original",
		"small": "https://images.unsplash.com/photo-1?w=400&ixid=original",
	},
	"links": {
		"html": "https://unsplash.com/photos/photo_A-1",
		"download_location": "https://api.unsplash.com/photos/photo_A-1/download?ixid=original",
	},
	"user": {"name": "Pat", "links": {"html": "https://unsplash.com/@pat"}},
}


def response(payload, status=200):
	return MagicMock(status_code=status, json=MagicMock(return_value=payload))


def unsplash_asset(**extra):
	return {
		"id": "unsplash:photo_A-1",
		"provider": "Unsplash",
		"url": UNSPLASH_PHOTO["urls"]["regular"],
		"thumb": UNSPLASH_PHOTO["urls"]["small"],
		"source_url": UNSPLASH_PHOTO["links"]["html"],
		"download_location": UNSPLASH_PHOTO["links"]["download_location"],
		"license_url": "https://unsplash.com/license",
		"requires_acquisition": True,
		"description": "Coastal landscape",
		"credit": "Pat",
		"size": "4000x3000",
		**extra,
	}


class OfflineAssetTest(unittest.TestCase):
	def setUp(self):
		self.enterContext(
			patch("requests.sessions.Session.request", side_effect=AssertionError("Network forbidden"))
		)
		self.conf = self.enterContext(patch.object(frappe, "conf", frappe._dict()))
		self.logger = self.enterContext(patch.object(frappe, "logger", return_value=MagicMock())).return_value


class TestMagnificStock(OfflineAssetTest):
	def test_search_contract_uses_only_search_endpoint_and_preview_fields(self):
		with patch("requests.get", return_value=response({"data": [STOCK_RESOURCE]})) as get:
			asset = MagnificStock("test-key").search("white t-shirt", "landscape")[0]
		get.assert_called_once_with(
			"https://api.magnific.com/v1/resources",
			params={
				"term": "white t-shirt",
				"limit": 6,
				"order": "relevance",
				"filters[content_type][photo]": 1,
				"filters[ai-generated][excluded]": 1,
				"filters[orientation][landscape]": 1,
			},
			headers={"x-magnific-api-key": "test-key"},
			timeout=10,
			allow_redirects=False,
		)
		self.assertEqual(asset["id"], "magnific:15667327")
		self.assertEqual(asset["provider_id"], "15667327")
		self.assertEqual(asset["source_url"], STOCK_RESOURCE["url"])
		self.assertEqual(asset["provider_licenses"], STOCK_RESOURCE["licenses"])
		self.assertEqual(asset["url"], "")
		self.assertTrue(asset["preview_only"])
		self.assertTrue(asset["requires_acquisition"])
		self.assertEqual(asset["license_status"], "preview_only")
		self.assertEqual(asset["thumb"], STOCK_RESOURCE["image"]["source"]["url"])

	def test_orientation_params_are_documented_nested_flags(self):
		provider = MagnificStock("test-key")
		for orientation in (None, "portrait", "square", "invalid"):
			with self.subTest(orientation=orientation):
				params = provider.search_params("shoe", orientation)
				flags = [key for key in params if "orientation" in key]
				self.assertEqual(
					flags,
					[f"filters[orientation][{orientation}]"] if orientation in images.ORIENTATIONS else [],
				)

	def test_missing_preview_or_original_and_non_photos_are_not_results(self):
		provider = MagnificStock("test-key")
		for patch_value in (
			{"id": None},
			{"id": True},
			{"image": {}},
			{"url": "javascript:alert(1)"},
			{"url": "https://example.com/photo"},
		):
			with self.subTest(patch_value=patch_value):
				self.assertIsNone(provider.preview({**STOCK_RESOURCE, **patch_value}))
		vector = deepcopy(STOCK_RESOURCE)
		vector["image"]["type"] = "vector"
		self.assertIsNone(provider.preview(vector))

	def test_api_result_count_is_bounded_even_if_server_ignores_limit(self):
		payload = {"data": [{**STOCK_RESOURCE, "id": i + 1} for i in range(30)]}
		with patch("requests.get", return_value=response(payload)):
			self.assertEqual(len(MagnificStock("test-key").search("shoe", None)), MAX_RESULTS)

	def test_redirect_is_not_followed_or_treated_as_success(self):
		with patch("requests.get", return_value=response({}, status=302)) as get:
			with self.assertRaises(ValueError):
				MagnificStock("test-key").search("shoe", None)
		self.assertFalse(get.call_args.kwargs["allow_redirects"])

	def test_render_has_id_link_and_manual_import_instead_of_page_url(self):
		asset = MagnificStock("test-key").preview(STOCK_RESOURCE)
		text = images.render_results("Magnific", [asset])
		self.assertIn("PREVIEW ONLY", text)
		self.assertIn("magnific:15667327", text)
		self.assertIn(STOCK_RESOURCE["url"], text)
		self.assertIn("upload the licensed file manually", text)
		self.assertNotIn("url: " + asset["thumb"], text)


class TestImageProviderRouting(OfflineAssetTest):
	def test_paid_provider_requires_explicit_opt_in_and_key(self):
		for config, enabled in (
			({}, False),
			({"magnific_api_key": "test-key"}, False),
			({"bob_stock_provider": "magnific"}, False),
			({"bob_stock_provider": "unknown", "magnific_api_key": "test-key"}, False),
			({"bob_stock_provider": "magnific", "magnific_api_key": "test-key"}, True),
		):
			with self.subTest(config=config):
				self.conf.clear()
				self.conf.update(config)
				names = [name for name, _search in images.providers()]
				self.assertEqual("Magnific" in names, enabled)
				self.assertEqual(names[-1], "Openverse")

	def test_existing_free_provider_order_is_preserved(self):
		self.conf.update(pexels_api_key="test-pexels", unsplash_access_key="test-unsplash")
		self.assertEqual([name for name, _search in images.providers()], ["Pexels", "Unsplash", "Openverse"])

	def test_explicit_disabled_provider_never_falls_back(self):
		with patch.object(images, "search_openverse") as fallback:
			result = images.run_search_images(SimpleNamespace(), {"query": "shoe", "provider": "magnific"})
		self.assertIn("unavailable", result)
		fallback.assert_not_called()

	def test_explicit_free_provider_skips_configured_paid_library(self):
		self.conf.update(bob_stock_provider="magnific", magnific_api_key="test-key")
		with (
			patch.object(MagnificStock, "search") as paid,
			patch.object(images, "search_openverse", return_value=[]) as free,
		):
			images.run_search_images(SimpleNamespace(), {"query": "shoe", "provider": "openverse"})
		paid.assert_not_called()
		free.assert_called_once_with("shoe", None)

	def test_auto_falls_back_on_error_without_logging_provider_response_or_secrets(self):
		self.conf.update(bob_stock_provider="magnific", magnific_api_key="test-key")
		with (
			patch.object(MagnificStock, "search", side_effect=requests.HTTPError("private-key-or-body")),
			patch.object(images, "search_openverse", return_value=[]) as free,
		):
			images.run_search_images(SimpleNamespace(), {"query": "shoe"})
		free.assert_called_once()
		self.assertNotIn("private-key-or-body", str(self.logger.warning.call_args))


class TestSearchInventory(OfflineAssetTest):
	def setUp(self):
		super().setUp()
		self.brief = self.enterContext(patch("builder.ai.brief.DesignBrief")).return_value
		self.brief.read.return_value = {"assets": []}

	def test_persists_search_even_without_turn_inventory(self):
		asset = MagnificStock("test-key").preview(STOCK_RESOURCE)
		images.remember_for_generation(SimpleNamespace(page_id="page-1"), "shirt", [asset])
		self.brief.remember_assets.assert_called_once_with([{**asset, "query": "shirt"}])

	def test_persists_after_turn_inventory_fills_up(self):
		ctx = SimpleNamespace(
			page_id="page-1", found_images=[unsplash_asset(id=f"unsplash:{i}") for i in range(24)]
		)
		images.remember_for_generation(ctx, "shirt", [MagnificStock("test-key").preview(STOCK_RESOURCE)])
		self.brief.remember_assets.assert_called_once()
		self.assertLessEqual(len(ctx.found_images), 24)
		self.assertIn("magnific:15667327", [a["id"] for a in ctx.found_images])

	def test_saved_selection_and_tracking_win_over_repeated_search(self):
		original = unsplash_asset(selected=True, download_tracked=True, requires_acquisition=False)
		self.brief.read.return_value = {"assets": [original]}
		ctx = SimpleNamespace(page_id="page-1", found_images=[original])
		results = images.remember_for_generation(
			ctx, "coast", [unsplash_asset(url="https://images.unsplash.com/new")]
		)
		self.assertEqual(results, [original])
		self.assertEqual(ctx.found_images, [original])

	def test_unsplash_search_preserves_identity_hotlink_and_tracking_location_without_tracking(self):
		with patch("requests.get", return_value=response({"results": [UNSPLASH_PHOTO]})) as get:
			asset = images.search_unsplash("coast", "square", "test-key")[0]
		get.assert_called_once()
		self.assertEqual(get.call_args.args[0], "https://api.unsplash.com/search/photos")
		self.assertEqual(get.call_args.kwargs["params"]["orientation"], "squarish")
		self.assertEqual(asset["url"], UNSPLASH_PHOTO["urls"]["regular"])
		self.assertEqual(asset["download_location"], UNSPLASH_PHOTO["links"]["download_location"])
		self.assertTrue(asset["requires_acquisition"])
		self.assertIn("utm_source=frappe_builder", asset["credit_url"])
		self.assertIn("utm_medium=referral", asset["source_url"])


class TestSelectedAcquisition(OfflineAssetTest):
	def setUp(self):
		super().setUp()
		self.conf.unsplash_access_key = "test-key"
		self.asset = unsplash_asset(selected=True)
		self.ctx = SimpleNamespace(page_id="page-1", found_images=[])
		self.brief = self.enterContext(patch("builder.ai.brief.DesignBrief")).return_value
		self.brief.read.return_value = {"assets": [self.asset]}
		self.doc = self.enterContext(patch.object(frappe, "get_doc")).return_value
		self.enterContext(patch.object(frappe, "db", MagicMock()))
		self.get = self.enterContext(
			patch("requests.get", return_value=response({"url": "https://do-not-use.example/download"}))
		)

	def acquire(self, asset_id="unsplash:photo_A-1"):
		return images.run_acquire_asset(self.ctx, {"asset_id": asset_id})

	def test_explicit_selection_tracks_saved_original_and_keeps_hotlink(self):
		result = self.acquire()
		self.doc.check_permission.assert_called_once_with("write")
		frappe.db.get_value.assert_called_once_with("Builder Page", "page-1", "name", for_update=True)
		self.get.assert_called_once_with(
			self.asset["download_location"],
			headers={"Authorization": "Client-ID test-key", "Accept-Version": "v1"},
			timeout=10,
			allow_redirects=False,
		)
		updated = self.brief.save.call_args.args[0]["assets"][0]
		self.assertTrue(updated["download_tracked"])
		self.assertFalse(updated["requires_acquisition"])
		self.assertEqual(updated["url"], self.asset["url"])
		self.assertEqual(updated["id"], self.asset["id"])
		self.assertIn(self.asset["url"], result)
		self.assertNotIn("do-not-use.example", result)
		self.assertEqual(self.ctx.found_images, [updated])

	def test_retry_on_later_turn_does_not_repeat_tracking(self):
		self.acquire()
		self.brief.read.return_value = self.brief.save.call_args.args[0]
		self.ctx.found_images = []
		self.acquire()
		self.get.assert_called_once()

	def test_unknown_or_unselected_ids_cannot_acquire(self):
		self.assertIn("FAILED", self.acquire("unsplash:invented"))
		self.asset.pop("selected")
		self.assertIn("FAILED", self.acquire())
		self.get.assert_not_called()

	def test_permission_denial_precedes_inventory_and_network_access(self):
		self.doc.check_permission.side_effect = frappe.PermissionError("Denied")
		with self.assertRaises(frappe.PermissionError):
			self.acquire()
		self.brief.read.assert_not_called()
		self.get.assert_not_called()

	def test_missing_page_or_provider_configuration_does_not_request(self):
		self.conf.clear()
		self.assertIn("not configured", self.acquire())
		self.ctx.page_id = None
		self.assertIn("saved page", self.acquire())
		self.get.assert_not_called()

	def test_paid_selected_asset_cannot_trigger_purchase(self):
		asset = {**MagnificStock("test-key").preview(STOCK_RESOURCE), "selected": True}
		self.brief.read.return_value = {"assets": [asset]}
		result = self.acquire(asset["id"])
		self.assertIn("PREVIEW ONLY", result)
		self.assertIn(asset["source_url"], result)
		self.get.assert_not_called()
		self.brief.save.assert_not_called()

	def test_download_location_must_match_saved_unsplash_original(self):
		for url in (
			"https://attacker.example/photos/photo_A-1/download",
			"http://api.unsplash.com/photos/photo_A-1/download",
			"https://api.unsplash.com@attacker.example/photos/photo_A-1/download",
			"https://api.unsplash.com/photos/another/download",
			"https://api.unsplash.com/photos/photo_A-1/download#fragment",
		):
			with self.subTest(url=url):
				self.asset["download_location"] = url
				self.assertIn("FAILED", self.acquire())
		self.get.assert_not_called()

	def test_provider_failure_does_not_mark_acquired_or_expose_details(self):
		self.get.side_effect = requests.Timeout("private-key-or-body")
		result = self.acquire()
		self.assertIn("FAILED", result)
		self.assertNotIn("private-key-or-body", result)
		self.brief.save.assert_not_called()
		self.assertEqual(self.ctx.found_images, [])

	def test_tracking_redirect_does_not_mark_acquired(self):
		self.get.return_value = response({}, status=302)
		self.assertIn("FAILED", self.acquire())
		self.brief.save.assert_not_called()


class TestAssetBriefIntegration(OfflineAssetTest):
	def test_acquisition_and_repeated_search_keep_selected_original_across_turns(self):
		from builder.ai.brief import DesignBrief

		original = unsplash_asset(selected=True)
		stored = {"brief": json.dumps({"project": "Coastal guide", "assets": [original]})}
		db = MagicMock()
		db.get_value.side_effect = lambda _doctype, _name, field, **kwargs: (
			stored["brief"] if field == "ai_design_brief" else "page-1"
		)
		db.set_value.side_effect = lambda _doctype, _name, _field, value, **kwargs: stored.update(brief=value)
		self.conf.unsplash_access_key = "test-key"
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=MagicMock()),
			patch("requests.get", return_value=response({})) as get,
		):
			ctx = SimpleNamespace(page_id="page-1", found_images=[])
			images.run_acquire_asset(ctx, {"asset_id": original["id"]})
			next_turn = SimpleNamespace(page_id="page-1", found_images=[])
			images.remember_for_generation(
				next_turn, "coast", [unsplash_asset(url="https://images.unsplash.com/changed")]
			)
			images.run_acquire_asset(next_turn, {"asset_id": original["id"]})
			brief = DesignBrief("page-1").read()
		get.assert_called_once()
		asset = brief["assets"][0]
		self.assertTrue(asset["selected"])
		self.assertTrue(asset["download_tracked"])
		self.assertFalse(asset["requires_acquisition"])
		self.assertEqual(asset["url"], original["url"])
		self.assertEqual(asset["download_location"], original["download_location"])
		self.assertEqual(brief["project"], "Coastal guide")
		self.assertEqual(next_turn.found_images, [asset])


if __name__ == "__main__":
	unittest.main()
