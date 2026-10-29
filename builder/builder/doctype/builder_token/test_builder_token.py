# Copyright (c) 2025, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import json
import os
import tempfile

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_page.builder_page import get_font_family, resolve_font_token
from builder.builder.doctype.builder_token.builder_token import get_css_variables, get_variables_css
from builder.builder.patches.refactor_builder_variables import build_maps, rewrite_doctype_blocks
from builder.utils import import_fixture_record, normalize_renamed_doc, sync_builder_tokens


def make_token(**kwargs):
	defaults = {"doctype": "Builder Token", "token_name": "test-token", "type": "Color", "value": "#123456"}
	return frappe.get_doc({**defaults, **kwargs}).insert()


class TestBuilderToken(FrappeTestCase):
	def setUp(self):
		get_css_variables.clear_cache()

	def test_token_is_named_with_a_uuid(self):
		token = make_token(token_name="brand")
		self.assertRegex(token.name, r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

	def test_css_variable_uses_the_token_id_as_its_handle(self):
		token = make_token(token_name="with-value", value="#abcdef")
		css_variables, _ = get_css_variables()
		self.assertEqual(css_variables[f"--{token.name}"], "#abcdef")

	def test_dark_value_renders_as_light_dark(self):
		token = make_token(token_name="duotone", value="#ffffff", dark_value="#000000")
		self.assertIn(f"--{token.name}: light-dark(#ffffff, #000000);", get_variables_css())

	def test_matching_dark_value_renders_once(self):
		token = make_token(token_name="monotone", value="#ffffff", dark_value="#ffffff")
		self.assertIn(f"--{token.name}: #ffffff;", get_variables_css())

	def test_deleting_a_token_drops_it_from_the_css(self):
		token = make_token(token_name="short-lived", value="#333333")
		handle = f"--{token.name}"
		self.assertIn(handle, get_variables_css())
		token.delete()
		self.assertNotIn(handle, get_variables_css())

	def test_editing_a_token_busts_the_css_cache(self):
		token = make_token(token_name="cache-check", value="#111111")
		self.assertIn("#111111", get_variables_css())
		token.value = "#222222"
		token.save()
		self.assertIn("#222222", get_variables_css())


class TestFontToken(FrappeTestCase):
	def setUp(self):
		get_css_variables.clear_cache()

	def test_font_token_resolves_to_its_family(self):
		token = make_token(token_name="display", type="Font", value="Fraunces")
		self.assertEqual(resolve_font_token(f"var(--{token.name})"), "Fraunces")
		self.assertEqual(get_font_family(f"var(--{token.name})"), "Fraunces")

	def test_unknown_font_token_resolves_to_nothing(self):
		# an unresolvable token must not reach the Google Fonts URL builder
		self.assertEqual(resolve_font_token("var(--does-not-exist)"), "")

	def test_plain_font_stack_is_left_alone(self):
		self.assertEqual(get_font_family("Inter, sans-serif"), "Inter")


class TestRenamedFixtures(FrappeTestCase):
	"""Fixtures and template bundles written before the Builder Token rename."""

	def test_pre_rename_doc_is_mapped(self):
		docdict = {"doctype": "Builder Variable", "variable_name": "legacy", "value": "#fff"}
		normalize_renamed_doc(docdict)
		self.assertEqual(docdict["doctype"], "Builder Token")
		self.assertEqual(docdict["token_name"], "legacy")
		self.assertNotIn("variable_name", docdict)

	def test_a_current_doc_is_left_alone(self):
		docdict = {"doctype": "Builder Token", "token_name": "current", "value": "#fff"}
		self.assertEqual(normalize_renamed_doc(dict(docdict)), docdict)

	def test_token_name_already_present_wins(self):
		docdict = {"doctype": "Builder Variable", "variable_name": "old", "token_name": "new"}
		normalize_renamed_doc(docdict)
		self.assertEqual(docdict["token_name"], "new")

	def test_pre_rename_fixture_imports_as_a_token(self):
		name = frappe.generate_hash(length=10)
		fixture = {
			"doctype": "Builder Variable",
			"name": name,
			"variable_name": "fixture-color",
			"type": "Color",
			"value": "#123456",
			"modified": "2026-01-01 00:00:00",
		}
		with tempfile.TemporaryDirectory() as folder:
			path = os.path.join(folder, "fixture.json")
			with open(path, "w") as f:
				json.dump(fixture, f)
			import_fixture_record(path)

		self.assertEqual(frappe.db.get_value("Builder Token", name, "token_name"), "fixture-color")

	def test_current_fixture_imports_unchanged(self):
		name = frappe.generate_hash(length=10)
		fixture = {
			"doctype": "Builder Token",
			"name": name,
			"token_name": "current-fixture-color",
			"type": "Color",
			"value": "#abcdef",
			"modified": "2026-01-01 00:00:00",
		}
		with tempfile.TemporaryDirectory() as folder:
			path = os.path.join(folder, "fixture.json")
			with open(path, "w") as f:
				json.dump(fixture, f)
			import_fixture_record(path)

		self.assertEqual(frappe.db.get_value("Builder Token", name, "value"), "#abcdef")

	def test_syncing_standard_tokens_is_safe_without_fixtures(self):
		# after_install/after_migrate call this; builder ships no token fixtures
		sync_builder_tokens()

	def test_a_missing_fixture_is_not_an_error(self):
		with tempfile.TemporaryDirectory() as folder:
			import_fixture_record(os.path.join(folder, "nope.json"))


class TestUUIDRefactorPatch(FrappeTestCase):
	def test_build_maps_covers_every_legacy_name_shape(self):
		tokens = [
			frappe._dict(name="brand_primary", token_name="brandPrimary"),
			frappe._dict(name="a1b2c3d4e5", token_name="Accent"),
		]
		rename_map, css_rewrite_map = build_maps(tokens)

		self.assertEqual(set(rename_map), {"brand_primary", "a1b2c3d4e5"})
		# kebab-cased label, snake-cased doc name and the older hex hash all resolve
		self.assertEqual(css_rewrite_map["brand-primary"], rename_map["brand_primary"])
		self.assertEqual(css_rewrite_map["accent"], rename_map["a1b2c3d4e5"])
		self.assertEqual(css_rewrite_map["a1b2c3d4e5"], rename_map["a1b2c3d4e5"])

	def test_rewrite_reaches_svg_markup(self):
		blocks = [
			{
				"blockId": "root",
				"baseStyles": {"color": "var(--brand)", "border": "1px solid var(--brand-dark)"},
				"attributes": {"fill": "var(--brand)"},
				"innerHTML": '<svg style="color: var(--brand)"><path fill="var(--brand, #eee)"/></svg>',
			}
		]
		page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "rewrite-probe", "blocks": json.dumps(blocks)}
		).insert()

		updated = rewrite_doctype_blocks(
			"Builder Page", ["blocks"], {"brand": "new-brand", "brand-dark": "new-brand-dark"}
		)
		self.assertGreaterEqual(updated, 1)

		rewritten = frappe.db.get_value("Builder Page", page.name, "blocks")
		self.assertIn("var(--new-brand)", rewritten)
		self.assertIn("var(--new-brand, #eee)", rewritten)
		# longer keys match first, so brand-dark is not rewritten as brand
		self.assertIn("var(--new-brand-dark)", rewritten)
		self.assertNotIn("var(--brand", rewritten)

	def test_rewrite_without_a_map_touches_nothing(self):
		self.assertEqual(rewrite_doctype_blocks("Builder Page", ["blocks"], {}), 0)
