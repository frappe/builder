# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What a hosting app refuses in a page or component (builder_content_problems), on the paths that skip
validate: Builder's AI writes drafts, generated pages, page settings and component definitions with
frappe.db.set_value, and previews render a page on the server. frappe.page compiles its own site's page
into a public copy through Jinja with database access, so nothing it refuses may land or render there."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import page_writer
from builder.ai.agent.tools.data import write_page_data_script
from builder.ai.agent.tools.settings import set_page_settings
from builder.ai.agent.tree import update_definition
from builder.builder.tests.hosting_hooks import hosting_hooks, refuse_template_syntax

CLEAN_ROOT = {"blockId": "root", "element": "div", "children": [], "innerHTML": "Hello"}
JINJA_ROOT = {"blockId": "root", "element": "div", "children": [], "innerHTML": "{{ 6*7 }}"}


class TestContentAHostingAppRefuses(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Content Policy",
				"route": "test-content-policy",
				"published": 0,
				"blocks": json.dumps([CLEAN_ROOT]),
			}
		).insert()
		cls.component = frappe.get_doc(
			{"doctype": "Builder Component", "component_name": "Policy", "block": json.dumps(CLEAN_ROOT)}
		).insert()

	def stored(self, field):
		return frappe.db.get_value("Builder Page", self.page.name, field) or ""

	def test_a_refused_draft_is_not_saved(self):
		with hosting_hooks(builder_content_problems=[refuse_template_syntax]):
			with self.assertRaises(frappe.ValidationError):
				page_writer.save_draft_blocks(self.page.name, JINJA_ROOT)
			self.assertNotIn("{{", self.stored("draft_blocks"))

			page_writer.save_draft_blocks(self.page.name, CLEAN_ROOT)
		self.assertIn("Hello", self.stored("draft_blocks"))

	def test_without_a_hook_every_draft_is_saved(self):
		with hosting_hooks(builder_content_problems=[]):
			page_writer.save_draft_blocks(self.page.name, JINJA_ROOT)
		self.assertIn("{{", self.stored("draft_blocks"))

	def test_a_refused_generated_page_is_not_saved(self):
		with (
			hosting_hooks(builder_content_problems=[refuse_template_syntax]),
			patch.object(page_writer, "expand_page_markup", return_value=([JINJA_ROOT], "")),
			self.assertRaises(frappe.ValidationError),
		):
			page_writer.persist_page(self.page.name, "<div>{{ 6*7 }}</div>")
		self.assertNotIn("{{", self.stored("draft_blocks"))

	def test_refused_page_settings_are_not_saved(self):
		ctx = SimpleNamespace(page_id=self.page.name)
		with (
			hosting_hooks(builder_content_problems=[refuse_template_syntax]),
			self.assertRaises(frappe.ValidationError),
		):
			set_page_settings(ctx, {"head_html": "<meta content='{{ 6*7 }}'>"})
		self.assertEqual(self.stored("head_html"), "")

	def test_a_refused_page_data_script_is_neither_run_nor_saved(self):
		"""Bob's data script is test-run before it saves; the hosting app is asked before that run"""
		ctx = SimpleNamespace(page_id=self.page.name)
		with hosting_hooks(builder_content_problems=[refuse_template_syntax]):
			with (
				patch(
					"builder.ai.agent.tools.data.DataScriptTrial", **{"return_value.blocks_save": False}
				) as trial,
				self.assertRaises(frappe.ValidationError),
			):
				write_page_data_script(ctx, {"script": "data.title = '{{ 6*7 }}'"})
			trial.assert_not_called()
			self.assertEqual(self.stored("page_data_script"), "")

			out = write_page_data_script(ctx, {"script": "data.title = 'Hello'"})
		self.assertTrue(out.startswith("Saved"), out)
		self.assertEqual(self.stored("page_data_script"), "data.title = 'Hello'")

	def test_a_refused_component_definition_is_not_saved(self):
		def bind_jinja(definition):
			definition["innerHTML"] = "{{ 6*7 }}"

		with (
			hosting_hooks(builder_content_problems=[refuse_template_syntax]),
			self.assertRaises(frappe.ValidationError),
		):
			update_definition(self.component.name, bind_jinja)
		self.assertNotIn("{{", frappe.db.get_value("Builder Component", self.component.name, "block"))

	def test_a_refused_page_is_not_rendered_for_a_preview(self):
		# written past every check (the threat model): the preview must still not run it
		frappe.db.set_value("Builder Page", self.page.name, "draft_blocks", json.dumps([JINJA_ROOT]))
		page = frappe.get_doc("Builder Page", self.page.name)

		with hosting_hooks(builder_content_problems=[refuse_template_syntax]):
			markup = page.get_preview_html()

		self.assertNotIn("42", markup)
		self.assertIn("carries template syntax", markup)

	def test_the_hook_hears_that_the_page_is_about_to_render(self):
		calls = []

		def record(doc, rendering):
			calls.append(rendering)

		with (
			hosting_hooks(builder_content_problems=[refuse_template_syntax]),
			patch("builder.builder.tests.hosting_hooks.refuse_template_syntax", side_effect=record),
		):
			frappe.get_doc("Builder Page", self.page.name).get_preview_html()
			page_writer.save_draft_blocks(self.page.name, CLEAN_ROOT)
		self.assertEqual(calls, [True, False])
