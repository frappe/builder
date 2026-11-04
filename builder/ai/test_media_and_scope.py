import io
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from PIL import Image

from builder.ai import api, memory, workspace
from builder.ai.artifacts import Artifact
from builder.ai.brief import DesignBrief
from builder.ai.media import MediaRequest, crop_asset, raster
from builder.ai.session import AISession


class TestMediaAndScope(FrappeTestCase):
	def setUp(self):
		limits = patch.dict(frappe.conf, {"bob_media_daily_budget_usd": 100000})
		limits.start()
		self.addCleanup(limits.stop)
		self.page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Bob media regression"}).insert()
		self.session = AISession.create({"page": self.page.name})

	def test_pending_media_cannot_be_charged_twice(self):
		with patch.dict(frappe.conf, {"bob_media_budget_usd": 1}), patch.object(frappe.db, "commit"):
			request = MediaRequest(self.page.name, "fixture", {"asset": "same"}, 0.3)
			self.assertIsNone(request.reserve())
			with self.assertRaisesRegex(ValueError, "reconciliation"):
				MediaRequest(self.page.name, "fixture", {"asset": "same"}, 0.3).reserve()
			_, receipt = Artifact.get(request.name, self.page.name, "media_request")
			self.assertIsNone(receipt["actual_cost_usd"])

	def test_pending_media_surface_only_returns_requests_needing_review(self):
		with patch.dict(frappe.conf, {"bob_media_budget_usd": 1}), patch.object(frappe.db, "commit"):
			request = MediaRequest(self.page.name, "fixture", {"asset": "same"}, 0.3)
			request.reserve()
			Artifact.save(self.page.name, "media_request", {"reserved_usd": "0.2"}, status="complete")
			result = workspace.get_pending_media_requests(self.page.name)
		self.assertEqual(
			result["requests"], [{"id": request.name, "label": "fixture", "reserved_usd": "0.3"}]
		)
		self.assertTrue(result["can_reconcile"])

	def test_page_media_budget_is_enforced_before_external_work(self):
		with patch.dict(frappe.conf, {"bob_media_budget_usd": 0.5}), patch.object(frappe.db, "commit"):
			MediaRequest(self.page.name, "fixture", {"asset": "one"}, 0.3).reserve()
			with self.assertRaisesRegex(ValueError, "budget is exhausted"):
				MediaRequest(self.page.name, "fixture", {"asset": "two"}, 0.3).reserve()

	def test_crops_keep_source_credit_and_reuse_cached_raster(self):
		buffer = io.BytesIO()
		Image.new("RGB", (200, 100), "blue").save(buffer, "PNG")
		asset = {
			"id": "owned:photo",
			"provider": "Upload",
			"url": "/files/photo.png",
			"selected": True,
			"credit": "User's photo",
		}
		DesignBrief(self.page.name).remember_assets([asset])
		with (
			patch("builder.ai.media.asset_content", return_value=buffer.getvalue()) as source,
			patch(
				"builder.ai.media.save_raster",
				return_value={"url": "/files/crop.webp", "thumb": "/files/crop.webp"},
			),
		):
			first = crop_asset(self.page.name, asset["id"], 64, 96, 0.2, 0.5)
			second = crop_asset(self.page.name, asset["id"], 64, 96, 0.2, 0.5)
		self.assertEqual(first, second)
		self.assertEqual(source.call_count, 1)
		self.assertEqual(first["original_id"], "owned:photo")
		self.assertEqual(first["credit"], "User's photo")

	def test_svg_is_not_accepted_as_raster_artwork(self):
		with self.assertRaises(Exception):
			raster(b'<svg xmlns="http://www.w3.org/2000/svg"/>')

	def test_cached_artwork_does_not_redownload_source_or_charge(self):
		from builder.ai.media import generate_image

		with (
			patch.dict(frappe.conf, {"bob_image_model": "fixture", "bob_image_api_key": "fixture"}),
			patch("builder.ai.media.selected_asset", return_value={"url": "/files/owned.png"}),
			patch.object(MediaRequest, "cached", return_value={"url": "/files/finished.webp"}),
			patch("builder.ai.media.asset_content") as download,
			patch("builder.ai.media.requests.post") as charge,
		):
			self.assertEqual(
				generate_image(self.page.name, "Same image", source_asset="owned:1")["url"],
				"/files/finished.webp",
			)
			download.assert_not_called()
			charge.assert_not_called()

	def test_media_reconciliation_requires_settling_and_releases_only_verified_charge(self):
		from builder.ai.media import reconcile_request

		with patch.dict(frappe.conf, {"bob_media_budget_usd": 1}), patch.object(frappe.db, "commit"):
			request = MediaRequest(self.page.name, "fixture", {"asset": "recover"}, 0.3)
			request.reserve()
			with self.assertRaisesRegex(ValueError, "five minutes"):
				reconcile_request(
					self.page.name, request.name, "not_charged", "Confirmed in provider billing"
				)
			frappe.db.set_value(
				"Builder AI Artifact",
				request.name,
				"modified",
				frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-6),
				update_modified=False,
			)
			reconcile_request(self.page.name, request.name, "not_charged", "Confirmed in provider billing")
			self.assertIsNone(request.reserve())
			self.assertEqual(len(request.value["prior_reconciliations"]), 1)

	def test_action_reconciliation_never_repeats_callback(self):
		message_id = self.session.append_message(
			"assistant", "Apply action", metadata={"status": "action_applying"}
		)
		with self.assertRaisesRegex(ValueError, "five minutes"):
			api.reconcile_pending_action(message_id, "applied", "Verified the intended effect")
		frappe.db.set_value(
			"Builder AI Message",
			message_id,
			"modified",
			frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-6),
			update_modified=False,
		)
		with patch("builder.ai.agent.pending.apply_pending_action") as apply:
			api.reconcile_pending_action(message_id, "applied", "Verified the intended effect")
			apply.assert_not_called()
		self.assertEqual(frappe.db.get_value("Builder AI Message", message_id, "status"), "action_applied")
		with self.assertRaisesRegex(ValueError, "does not need"):
			api.reconcile_pending_action(message_id, "applied", "Verified the intended effect")

	def test_memory_scope_does_not_expose_other_users(self):
		owned = frappe._dict(scope="user", memory_user="alice@example.test", owner="alice@example.test")
		self.assertTrue(memory.has_permission(owned, user="alice@example.test", permission_type="read"))
		self.assertFalse(memory.has_permission(owned, user="bob@example.test", permission_type="read"))
		self.assertIn("memory_user", memory.permission_query("bob@example.test"))

	def test_page_memory_does_not_bleed_into_other_pages(self):
		frappe.get_doc(
			{
				"doctype": memory.DOCTYPE,
				"content": "Only this page uses euros",
				"scope": "page",
				"page": self.page.name,
			}
		).insert()
		self.assertTrue(
			any(row.content == "Only this page uses euros" for row in memory.visible(self.page.name))
		)
		self.assertFalse(any(row.content == "Only this page uses euros" for row in memory.visible(None)))

	def test_deleted_chat_is_tombstoned_and_cannot_be_recreated_by_late_worker(self):
		self.session.append_message("user", "Delete this conversation")
		api.delete_ai_session(self.session.name)
		self.assertEqual(frappe.db.get_value(AISession.DOCTYPE, self.session.name, "status"), "Deleted")
		self.assertIsNone(AISession.try_append_message(self.session.name, "assistant", "Late reply"))
		with self.assertRaisesRegex(Exception, "deleted"):
			AISession.get(self.session.name)
		self.assertEqual(
			api.get_ai_session(self.page.name, session_id=self.session.name)["deleted_session"],
			self.session.name,
		)
