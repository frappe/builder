import copy
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from jinja2 import TemplateNotFound, UndefinedError

from builder.ai import cards, design, projects
from builder.ai.artifacts import Artifact
from builder.ai.block_codec import BlockCodec
from builder.ai.brief import DesignBrief
from builder.ai.budgets import ContextBudgetError, estimate_tokens, fit_request
from builder.ai.content_locks import preserve_locked
from builder.ai.credits import add_asset_credits
from builder.ai.policies import CORE
from builder.ai.session import AISession
from builder.ai.workflow import ModelRequest
from builder.ai.workspace import update_decisions


class TestDesignWorkflow(FrappeTestCase):
	def setUp(self):
		self.page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Bob workflow regression"}
		).insert()
		self.session = AISession.create({"page": self.page.name})

	def test_native_preview_has_no_frappe_template_globals(self):
		root = {
			"blockId": "preview",
			"element": "div",
			"originalElement": "body",
			"children": [{"blockId": "copy", "element": "p", "innerHTML": "A real studio"}],
		}
		self.assertIn("A real studio", design.candidate_markup(root))
		root["children"][0]["innerHTML"] = "{{ frappe.db.get_value('User', 'Administrator', 'email') }}"
		with self.assertRaises(UndefinedError):
			design.candidate_markup(root)
		root["children"][0]["innerHTML"] = "{% include 'site_config.json' %}"
		with self.assertRaises(TemplateNotFound):
			design.candidate_markup(root)

	def test_cached_raster_variant_promotes_exact_native_blocks(self):
		DesignBrief(self.page.name).update({"project": "Real user's studio", "goal": "Book a visit"})
		with patch.object(design, "save_preview", return_value="/private/files/desktop.webp") as render:
			first = design.create_direction(self.page.name, {"label": "Quiet", "recipe": "compact"})
			second = design.create_direction(self.page.name, {"label": "Quiet", "recipe": "compact"})
		self.assertEqual(render.call_count, 1)
		self.assertEqual(first, second)
		self.assertNotIn("mobile_image", first)
		_, candidate = Artifact.get(first["variant_id"], self.page.name, "design")
		operations = []
		ctx = SimpleNamespace(
			page_id=self.page.name, ensure_revert_snapshot=lambda: None, queue_client_op=operations.append
		)
		design.apply_direction(ctx, first["variant_id"])
		self.assertEqual(
			json.loads(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"))[0],
			candidate["blocks"],
		)
		self.assertEqual(operations[0]["args"]["blocks"], candidate["blocks"])

	def test_tweak_keeps_base_specification_and_page_unchanged(self):
		DesignBrief(self.page.name).update({"project": "A real studio"})
		before = frappe.db.get_value("Builder Page", self.page.name, "draft_blocks")
		with patch.object(design, "save_preview", return_value="/private/files/desktop.webp"):
			base = design.create_direction(
				self.page.name,
				{
					"label": "Original",
					"recipe": "compact",
					"headline": "User headline",
					"palette": {"background": "#ffffff", "text": "#222222", "accent": "#0000ff"},
				},
			)
			revised = design.create_direction(
				self.page.name,
				{
					"label": "Warmer",
					"base_variant_id": base["variant_id"],
					"palette": {"accent": "#ff9900"},
				},
			)
		_, original = Artifact.get(base["variant_id"], self.page.name, "design")
		_, updated = Artifact.get(revised["variant_id"], self.page.name, "design")
		self.assertNotEqual(base["variant_id"], revised["variant_id"])
		self.assertEqual(updated["spec"]["headline"], "User headline")
		self.assertEqual(updated["spec"]["recipe"], "compact")
		self.assertEqual(
			updated["spec"]["palette"], {"background": "#ffffff", "text": "#222222", "accent": "#ff9900"}
		)
		self.assertEqual(original["spec"]["palette"]["accent"], "#0000ff")
		self.assertEqual(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"), before)

	def test_custom_direction_requires_yaml_changes_instead_of_ignored_recipe_fields(self):
		with self.assertRaisesRegex(ValueError, "edited YAML"):
			design.revised_spec({"yaml": "el: div"}, {"font": "Inter"})
		self.assertEqual(
			design.revised_spec({"yaml": "el: div"}, {"yaml": "el: section"})["yaml"], "el: section"
		)

	def test_detail_previews_crop_existing_pixels_and_remain_private(self):
		from PIL import Image

		buffer = BytesIO()
		Image.new("RGB", (400, 200), "#aa0000").save(buffer, format="WEBP")
		with patch(
			"frappe.utils.file_manager.save_file",
			return_value=SimpleNamespace(file_url="/private/files/detail.webp"),
		) as save:
			details = design.save_detail_previews(
				self.page.name,
				"fixture",
				buffer.getvalue(),
				[{"label": "Contact", "box": (10, 20, 310, 120)}],
			)
		self.assertEqual(details, [{"label": "Contact", "image": "/private/files/detail.webp"}])
		self.assertEqual(Image.open(BytesIO(save.call_args.args[1])).size, (300, 100))
		self.assertTrue(save.call_args.kwargs["is_private"])
		self.assertEqual(save.call_args.args[3], self.page.name)

	def test_preview_regions_clip_to_captured_image_and_skip_offscreen_or_full_page(self):
		from builder.html_preview_image import preview_regions

		page = SimpleNamespace(
			send=lambda *args: (
				{
					"result": {
						"value": [
							{"label": "Whole", "x": 0, "y": 0, "width": 1280, "height": 1800},
							{"label": "Contact", "x": -20, "y": 1700, "width": 600, "height": 300},
							{"label": "Offscreen", "x": 0, "y": 2000, "width": 600, "height": 300},
						]
					}
				},
				None,
			)
		)
		self.assertEqual(
			preview_regions(page, 1280, 1800), [{"label": "Contact", "box": (0, 1700, 580, 1800)}]
		)

	def test_changed_brief_invalidates_direction(self):
		DesignBrief(self.page.name).update({"project": "Original"})
		with patch.object(design, "save_preview", return_value="/private/files/fixture.webp"):
			variant = design.create_direction(self.page.name, {"label": "Original"})
		DesignBrief(self.page.name).update({"project": "Corrected"})
		with self.assertRaisesRegex(ValueError, "brief changed"):
			design.apply_direction(SimpleNamespace(page_id=self.page.name), variant["variant_id"])

	def test_user_decision_cannot_be_silently_replaced_by_model(self):
		brief = {}
		update_decisions(
			brief, {"facts": [{"id": "currency", "value": "EUR", "status": "accepted"}]}, user_edit=True
		)
		with self.assertRaisesRegex(ValueError, "user-approved"):
			update_decisions(brief, {"facts": [{"id": "currency", "value": "USD"}]})
		self.assertEqual(brief["facts"][0]["value"], "EUR")

	def test_typed_card_rejects_double_answer_and_keeps_canonical_label(self):
		card = self.session.append_message(
			"assistant",
			"Direction?",
			metadata={
				"status": "ui",
				"ui": [
					{"id": "direction", "kind": "choices", "options": [{"id": "a", "label": "Calm: 日本語"}]}
				],
			},
		)
		answer = {
			"cardId": card,
			"answers": [{"fieldId": "direction", "optionIds": ["a"], "value": "forged label"}],
		}
		clean = cards.validate_card_answer(self.session.name, answer)
		self.assertEqual(clean["answers"][0]["value"], ["Calm: 日本語"])
		cards.consume_questions(self.session.name, "answer-message", clean)
		with self.assertRaisesRegex(ValueError, "already been answered"):
			cards.validate_card_answer(self.session.name, answer)

	def test_free_text_retires_card_without_fabricating_answers(self):
		card = self.session.append_message("assistant", "Direction?", metadata={"status": "ui", "ui": []})
		cards.consume_questions(self.session.name, "free-text", None)
		row = frappe.get_doc("Builder AI Message", card)
		self.assertEqual(row.status, "ui_replaced")
		self.assertIsNone(json.loads(row.metadata_json)["answer"])

	def test_project_rejects_cycles_and_stale_revision(self):
		with self.assertRaisesRegex(ValueError, "cycle"):
			projects.validate_tasks([{"id": "a", "depends_on": ["b"]}, {"id": "b", "depends_on": ["a"]}])
		project = projects.save_project(
			self.page.name,
			"Site",
			tasks=[{"id": "home", "title": "Home", "page": self.page.name, "status": "pending"}],
		)
		self.assertEqual(project["revision"], 1)
		with self.assertRaisesRegex(ValueError, "project changed"):
			projects.save_project(self.page.name, "Old plan", tasks=[], expected_revision=0)

	def test_project_draft_creation_is_idempotent(self):
		projects.save_project(
			self.page.name,
			"Site",
			tasks=[
				{
					"id": "about",
					"title": "About",
					"route": f"bob-regression-{self.page.name}",
					"status": "pending",
				}
			],
		)
		first = projects.create_project_page(self.page.name, "about")
		second = projects.create_project_page(self.page.name, "about")
		self.assertEqual(first["page"], second["page"])

	def test_codec_preserves_pins_props_visibility_and_binding_metadata(self):
		block = {
			"element": "p",
			"blockId": "label",
			"componentVersion": "v1",
			"props": {"label": {"default": "Hello", "type": "String"}},
			"visibilityCondition": {"key": "available"},
			"dynamicValues": [
				{
					"key": "label",
					"property": "innerHTML",
					"comesFrom": "props",
					"type": "key",
					"fallback": "Hello",
				}
			],
			"editorConfig": {"aiLocked": True},
		}
		out = BlockCodec.expand(BlockCodec.compress(block))
		for key in block:
			self.assertEqual(out[key], block[key])

	def test_protected_content_blocks_edit_removal_and_reparenting(self):
		root = {
			"blockId": "root",
			"children": [
				{"blockId": "hero", "innerHTML": "User copy", "editorConfig": {"aiLocked": True}},
				{"blockId": "other", "children": []},
			],
		}
		for change in ("edit", "remove", "reparent"):
			after = copy.deepcopy(root)
			if change == "edit":
				after["children"][0]["innerHTML"] = "Changed"
			elif change == "remove":
				after["children"].pop(0)
			else:
				after["children"][1]["children"].append(after["children"].pop(0))
			with self.subTest(change=change), self.assertRaises(ValueError):
				preserve_locked(root, after)

	def test_editing_compact_bindings_overrides_preserved_metadata(self):
		from builder.ai.page_writer import convert_yaml_block

		block = {
			"element": "p",
			"blockId": "copy",
			"dynamicValues": [{"property": "innerHTML", "key": "old", "type": "key", "fallback": "original"}],
		}
		compact = BlockCodec.compress(block)
		compact["bind"]["innerHTML"] = "new"
		for expand in (BlockCodec.expand, convert_yaml_block):
			self.assertEqual(expand(compact)["dynamicValues"][0]["key"], "new")
			self.assertEqual(expand(compact)["blockId"], "copy")
		compact["bind"] = {}
		self.assertEqual(BlockCodec.expand(compact)["dynamicValues"], [])

	def test_credit_is_delivered_once_with_source_and_license(self):
		root = {
			"element": "div",
			"children": [{"element": "img", "attributes": {"src": "https://example.com/image.webp"}}],
		}
		assets = [
			{
				"id": "photo",
				"provider": "Openverse",
				"url": "https://example.com/image.webp",
				"credit": "Creator",
				"source_url": "https://example.com/creator",
				"license_url": "https://example.com/license",
			}
		]
		add_asset_credits(root, assets)
		add_asset_credits(root, assets)
		self.assertEqual(len(root["children"]), 2)
		self.assertIn("https://example.com/license", root["children"][-1]["innerHTML"])

	def test_context_budget_preserves_current_request_and_tool_pairs(self):
		messages = [
			{"role": "system", "content": CORE},
			{"role": "user", "content": "old history " * 12000},
			{"role": "assistant", "tool_calls": [{"id": "old"}], "content": None},
			{"role": "tool", "tool_call_id": "old", "content": "old result " * 9000},
			{"role": "user", "content": "Keep all prices in euros", "_bob_keep": True},
		]
		request = ModelRequest("fixture", messages, {"max_tokens": 2048})
		budget = fit_request(request, 8192)
		self.assertGreater(budget["removed_messages"], 0)
		self.assertEqual(request.messages[-1]["content"], "Keep all prices in euros")
		self.assertFalse(any(message.get("tool_call_id") == "old" for message in request.messages))
		self.assertLess(estimate_tokens([{"role": "system", "content": CORE}]), 2300)

	def test_oversized_required_request_is_rejected_before_provider_call(self):
		request = ModelRequest(
			"fixture",
			[
				{"role": "system", "content": CORE},
				{"role": "user", "content": "required " * 20000, "_bob_keep": True},
			],
			{"max_tokens": 2048},
		)
		with self.assertRaises(ContextBudgetError):
			fit_request(request, 8192)
