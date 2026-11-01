"""Offline regressions for the tool acceptance, read, generation and form boundaries.

Run with the bench Python via unittest; no site initialization or provider calls.
The JS fixture executes generated handlers in jsdom with an in-memory fetch stub.
"""

import json
import logging
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
import yaml

with patch.object(frappe, "logger", return_value=logging.getLogger(__name__)):
	from builder.ai import page_writer
	from builder.ai.agent import pending
	from builder.ai.agent.tools import data, forms, python
	from builder.ai.agent.tree import WorkingTree
	from builder.ai.block_codec import BlockCodec


class ReadableDocument:
	def __init__(self, denied=False):
		self.name = "fixture"
		self.denied = denied
		self.events = []
		self.values = {
			"name": self.name,
			"public": "hello",
			"private": "restricted",
			"rows": [{"private": "child secret"}],
		}

	def check_permission(self, permission):
		self.events.append(permission)
		if self.denied:
			raise frappe.PermissionError("Record read denied")

	def apply_fieldlevel_read_permissions(self):
		self.events.append("fields")
		self.values.pop("private")
		self.values["rows"] = [{}]

	def as_dict(self):
		self.events.append("serialize")
		return deepcopy(self.values)

	def get(self, field):
		return self.values.get(field)


class TestPermissionReads(unittest.TestCase):
	def setUp(self):
		self.doc = ReadableDocument()
		self.meta = SimpleNamespace(issingle=False, fields=[])
		for target, value in (
			("db", MagicMock()),
			("get_doc", MagicMock(side_effect=lambda *a: self.doc)),
			("get_meta", MagicMock(return_value=self.meta)),
			("has_permission", MagicMock(return_value=True)),
		):
			self.enterContext(patch.object(frappe, target, value))

	def read(self, **args):
		return json.loads(data.get_document(None, {"doctype": "Fixture", "name": "fixture", **args}))

	def test_denied_record_is_never_serialized(self):
		self.doc.denied = True
		self.assertEqual(self.read(fields=["private"]), {"error": "Record read denied"})
		self.assertEqual(self.doc.events, ["read"])

	def test_requested_fields_and_children_are_filtered_before_serialization(self):
		out = self.read(fields=["public", "private", "rows", "typo"])
		self.assertEqual(out["public"], "hello")
		self.assertEqual(out["rows"], [{}])
		self.assertNotIn("restricted", json.dumps(out))
		self.assertIn("no field 'typo'", out["typo"])
		self.assertEqual(self.doc.events, ["read", "fields", "serialize"])

	def test_doctype_denial_does_not_fetch_a_document(self):
		frappe.has_permission.return_value = False
		self.assertIn("permission", self.read()["error"])
		frappe.get_doc.assert_not_called()

	def test_single_document_uses_uncached_permission_checked_read(self):
		self.meta.issingle = True
		self.assertEqual(self.read(fields=["public"]), {"public": "hello"})
		frappe.get_doc.assert_called_once_with("Fixture")
		self.assertEqual(self.doc.events, ["read", "fields", "serialize"])

	def test_python_single_value_uses_the_same_field_filter(self):
		self.assertIsNone(python.user_get_single_value("Fixture", "private"))
		self.assertEqual(self.doc.events, ["read", "fields"])

	def test_python_single_get_value_preserves_projection_and_filters(self):
		self.meta.issingle = True
		out = python.user_get_value("Fixture", fieldname=["public", "private"], as_dict=True)
		self.assertEqual(out, {"public": "hello", "private": None})
		self.assertEqual(self.doc.events, ["read", "fields"])


class TestAcceptedOperations(unittest.TestCase):
	def setUp(self):
		self.root = {
			"blockId": "root",
			"children": [
				{"blockId": "title", "element": "h1", "innerHTML": "Original"},
				{"blockId": "copy", "element": "p", "innerHTML": "Keep"},
			],
		}
		self.tree = WorkingTree(self.root)

	def test_partial_bulk_replays_only_detached_normalized_accepted_patches(self):
		before = deepcopy(self.root)
		args = {
			"patches": [
				{
					"block_id": "title",
					"element": " H2 ",
					"base_styles": {"font-size": 30},
					"inner_text": "New",
				},
				{"block_id": "copy", "inner_text": "{{ missing.title }}"},
				{"block_id": "absent", "inner_text": "Missing"},
			]
		}
		result = self.tree.apply("update_blocks", args)
		self.assertIn("Applied to 1 of 3", result)
		self.assertIn("REJECTED", result)
		ops = self.tree.accepted_operations
		self.assertEqual(
			ops,
			[
				{
					"tool_name": "update_block",
					"args": {
						"block_id": "title",
						"element": "h2",
						"base_styles": {"fontSize": "30px"},
						"inner_text": "New",
					},
				}
			],
		)
		replay = WorkingTree(before)
		for op in ops:
			replay.apply(op["tool_name"], op["args"])
		self.assertEqual(replay.root, self.root)
		args["patches"][0]["base_styles"]["font-size"] = 99
		self.tree.resolve("title")["baseStyles"]["fontSize"] = "1px"
		self.assertEqual(ops[0]["args"]["base_styles"], {"fontSize": "30px"})

	def test_all_rejected_bulk_is_failed_and_resets_previous_acceptance(self):
		self.tree.apply("update_block", {"block_id": "title", "inner_text": "Valid"})
		before = deepcopy(self.root)
		result = self.tree.apply(
			"update_blocks",
			{
				"patches": [
					{"block_id": "title", "element": " SCRIPT ", "inner_text": "Bad"},
					{"block_id": "copy", "bind": {"src": "a + b"}},
				]
			},
		)
		self.assertTrue(result.startswith("FAILED:"))
		self.assertEqual(self.tree.accepted_operations, [])
		self.assertEqual(self.root, before)

	def test_uniform_bulk_and_repeated_targets_replay_in_order(self):
		self.tree.apply("update_blocks", {"block_ids": ["title", "copy"], "base_styles": {"margin-top": 8}})
		self.assertEqual([op["args"]["block_id"] for op in self.tree.accepted_operations], ["title", "copy"])
		self.tree.apply(
			"update_blocks",
			{
				"patches": [
					{"block_id": "title", "inner_text": "First"},
					{"block_id": "title", "inner_text": "Last"},
				]
			},
		)
		self.assertEqual(
			[op["args"]["inner_text"] for op in self.tree.accepted_operations], ["First", "Last"]
		)
		self.assertEqual(self.tree.resolve("title")["innerHTML"], "Last")

	def test_unsets_survive_compression_without_stale_attribute_aliases(self):
		title = self.tree.resolve("title")
		title.update(
			baseStyles={"paddingTop": "4px"},
			mobileStyles={"display": "none"},
			tabletStyles={"gap": "8px"},
			attributes={"id": "old", "aria-label": "old", "href": "old"},
			customAttributes={"id": "new", "aria-label": "new", "href": "stale"},
		)
		patch_args = {
			"block_id": "title",
			"base_styles": {"padding-top": None},
			"mobile_styles": {"display": None},
			"tablet_styles": {"gap": None},
			"attributes": {"id": None, "aria-label": None, "href": None},
		}
		self.tree.apply("update_block", patch_args)
		restored = BlockCodec.expand(BlockCodec.compress(title))
		for key in ("baseStyles", "mobileStyles", "tabletStyles", "attributes", "customAttributes"):
			self.assertFalse(restored.get(key))
		self.assertIsNone(self.tree.accepted_operations[0]["args"]["base_styles"]["paddingTop"])

	def test_binding_aliases_have_one_canonical_value_and_null_unbinds(self):
		self.tree.apply(
			"update_block", {"block_id": "title", "bind": {"text": "data.first", "innerHTML": "data.last"}}
		)
		self.assertEqual(
			self.tree.resolve("title")["dynamicValues"],
			[{"key": "last", "property": "innerHTML", "type": "key"}],
		)
		self.tree.apply("update_block", {"block_id": "title", "bind": {"text": None}})
		self.assertEqual(self.tree.resolve("title")["dynamicValues"], [])

	def test_root_removal_and_inline_add_data_are_rejected_without_mutation(self):
		before = deepcopy(self.root)
		self.assertTrue(self.tree.apply("remove_block", {"block_id": "root"}).startswith("FAILED:"))
		result = self.tree.apply(
			"add_block",
			{
				"parent_block_id": "root",
				"block": {
					"el": "div",
					"repeat": {"data": "cards", "items": [], "item": {"el": "p"}},
				},
			},
		)
		self.assertIn("cannot save repeat.items", result)
		self.assertEqual(self.tree.accepted_operations, [])
		self.assertEqual(self.root, before)


def repeater(items=None, key="data.catalog.cards"):
	return {
		"el": "div",
		"repeat": {
			"data": key,
			"items": items
			if items is not None
			else [
				{"enabled": True, "hidden": False, "optional": None, "title": "O'Reilly — 東京\nnext"},
			],
			"item": {"el": "p", "bind": {"text": "title"}},
		},
	}


class TestRepeaterCompilation(unittest.TestCase):
	def execute(self, script):
		from frappe.utils.safe_exec import FrappeTransformer
		from frappe.utils.safe_exec import _getattr_for_safe_exec as guarded_getattr
		from frappe.utils.safe_exec import _getitem as guarded_getitem
		from frappe.utils.safe_exec import _write as guarded_write
		from RestrictedPython import compile_restricted

		data = {}
		exec(compile(script, "<generated repeater>", "exec"), {"__builtins__": {}, "data": data})
		restricted = {}
		exec(
			compile_restricted(script, policy=FrappeTransformer),
			{
				"__builtins__": {},
				"data": restricted,
				"_getattr_": guarded_getattr,
				"_getitem_": guarded_getitem,
				"_write_": guarded_write,
			},
		)
		self.assertEqual(restricted, data)
		return data

	def test_wrapped_roots_compile_json_values_and_normalize_binding_keys(self):
		for wrap in (
			lambda n: n,
			lambda n: [n],
			lambda n: {"root": n},
			lambda n: {"page": n},
			lambda n: {"body": n},
		):
			with self.subTest(wrapper=wrap):
				node = repeater()
				blocks, script = page_writer.expand_page_yaml(yaml.safe_dump(wrap(node)))
				self.assertEqual(blocks[0]["dataKey"]["key"], "catalog.cards")
				self.assertEqual(self.execute(script), {"catalog": {"cards": node["repeat"]["items"]}})

	def test_nested_inline_data_is_attached_to_each_parent_record(self):
		node = repeater(items=[{"title": "A"}, {"title": "B"}], key="groups")
		node["repeat"]["item"] = repeater(items=[{"value": None, "live": True}], key="item.details.items")
		before = deepcopy(node)
		script = page_writer.build_repeater_data_script(node)
		result = self.execute(script)
		for item in result["groups"]:
			self.assertEqual(item["details"]["items"], [{"value": None, "live": True}])
		self.assertEqual(node, before)
		self.assertNotIn("details", result)

	def test_existing_nested_data_can_drive_a_nested_repeater_without_a_shim(self):
		node = repeater(items=[{"children": [{"live": True}]}], key="groups")
		node["repeat"]["item"] = {"el": "div", "repeat": {"data": "item.children", "item": {"el": "p"}}}
		blocks, script = page_writer.expand_page_yaml(yaml.safe_dump(node))
		self.assertEqual(self.execute(script)["groups"], node["repeat"]["items"])
		self.assertEqual(blocks[0]["children"][0]["dataKey"]["key"], "children")

	def test_duplicate_and_overlapping_data_keys_are_rejected(self):
		for key in ("catalog.cards", "data.catalog.cards", "catalog.cards.children", "catalog"):
			with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Conflicting"):
				page_writer.build_repeater_data_script({"el": "div", "c": [repeater(), repeater(key=key)]})

	def test_invalid_keys_items_and_templates_are_rejected(self):
		for key in (
			"",
			"cards..title",
			"cards[0]",
			"cards; fail()",
			"_private.cards",
			"catalog._private",
			"True",
			"none",
		):
			with self.subTest(key=key), self.assertRaises(ValueError):
				page_writer.expand_page_yaml(yaml.safe_dump(repeater(key=key)))
		for value in ({}, "cards", None):
			node = repeater()
			node["repeat"]["items"] = value
			with self.subTest(items=value), self.assertRaisesRegex(ValueError, "must be a list"):
				page_writer.build_repeater_data_script(node)
		with self.assertRaisesRegex(ValueError, "template block"):
			page_writer.convert_yaml_block({"el": "div", "repeat": {"data": "x", "item": "bad"}})

	def test_existing_script_is_preserved_and_no_partial_page_write_occurs(self):
		db = MagicMock()
		db.get_value.return_value = "data.existing = 'preserve this'"
		with patch.object(frappe, "db", db), self.assertRaisesRegex(ValueError, "existing page_data_script"):
			page_writer.persist_page("fixture", yaml.safe_dump(repeater()))
		db.set_value.assert_not_called()

	def test_data_only_binding_leaves_existing_script_untouched(self):
		node = repeater()
		del node["repeat"]["items"]
		db = MagicMock()
		with patch.object(frappe, "db", db):
			page_writer.persist_page("fixture", yaml.safe_dump(node))
		self.assertNotIn("page_data_script", db.set_value.call_args.args[2])

	def test_compressed_repeater_reconstructs_with_its_template(self):
		block = page_writer.convert_yaml_block(repeater())
		out = page_writer.convert_yaml_block(BlockCodec.compress(block))
		self.assertTrue(out["isRepeaterBlock"])
		self.assertEqual(out["dataKey"], block["dataKey"])
		self.assertEqual(out["children"][0]["dynamicValues"], block["children"][0]["dynamicValues"])


class TestIconRoundtrip(unittest.TestCase):
	def test_identity_attributes_classes_and_responsive_styles_survive_deep_simple_read(self):
		icon = page_writer.convert_icon_block(
			{
				"icon": "star",
				"attrs": {"aria-label": "Favorite", "id": "star"},
				"classes": ["favorite"],
				"m_style": {"display": "none"},
				"t_style": {"width": "20px"},
			}
		)
		out = BlockCodec.compress(icon, depth=4, task_tier="simple")
		self.assertEqual(out["ref"], icon["blockId"])
		self.assertEqual(out["attrs"]["aria-label"], "Favorite")
		restored = BlockCodec.expand(out)
		for key in (
			"blockId",
			"attributes",
			"customAttributes",
			"classes",
			"baseStyles",
			"mobileStyles",
			"tabletStyles",
		):
			self.assertEqual(restored.get(key), icon.get(key))

	def test_unset_icon_defaults_are_not_reintroduced_on_roundtrip(self):
		icon = page_writer.convert_icon_block({"icon": "star"})
		tree = WorkingTree(icon)
		tree.apply(
			"update_block", {"block_id": icon["blockId"], "base_styles": {"width": None, "display": None}}
		)
		restored = BlockCodec.expand(BlockCodec.compress(icon))
		self.assertEqual(restored["baseStyles"], icon["baseStyles"])
		self.assertNotIn("width", restored["baseStyles"])
		self.assertNotIn("display", restored["baseStyles"])


class TestFormMapping(unittest.TestCase):
	def test_reserved_names_keep_exact_original_html_mapping_across_confirmation(self):
		fields = forms.normalize_fields(
			[
				{"fieldname": "name", "input_name": "Full Name", "required": True},
				{"fieldname": "choices", "multiple": True},
			]
		)
		self.assertEqual(fields[0]["input_name"], "Full Name")
		self.assertEqual(fields[0]["fieldname"], "name_field")
		self.assertEqual(fields[0]["reqd"], 1)
		self.assertEqual(fields[1]["fieldtype"], "Text")
		self.assertEqual(forms.normalize_fields(fields), fields)

	def test_duplicate_mappings_are_rejected(self):
		for fields in (
			[{"fieldname": "name"}, {"fieldname": "name_field"}],
			[{"fieldname": "first", "input_name": "same"}, {"fieldname": "second", "input_name": "same"}],
		):
			with self.assertRaisesRegex(ValueError, "Duplicate"):
				forms.normalize_fields(fields)

	def test_page_and_selector_each_change_script_identity(self):
		names = {
			forms.form_script_name(page, "Contact", "contact", selector)
			for page in ("A", "B")
			for selector in ("#contact", "#signup")
		}
		self.assertEqual(len(names), 4)
		self.assertEqual(
			forms.form_script_name("A", "Contact", "contact", "#contact"),
			forms.form_script_name("A", "Contact", "contact", "#contact"),
		)

	def test_existing_connection_is_selector_specific(self):
		name = forms.form_script_name("A", "Contact", "contact", "#first")
		with patch.object(frappe, "db", MagicMock()), patch.object(frappe, "get_all", return_value=[name]):
			self.assertEqual(forms.connected_submission_doctype("A", "#first"), "Contact")
			self.assertIsNone(forms.connected_submission_doctype("A", "#second"))

	def test_attaching_same_submission_type_does_not_overwrite_another_pages_script(self):
		scripts, pages = {}, {}
		for name in ("A", "B"):
			page = MagicMock()
			page.get.return_value = []
			pages[name] = page

		def get_doc(doctype, name=None):
			if isinstance(doctype, dict):
				doc = MagicMock()
				doc.name, doc.script = doctype["name"], doctype["script"]
				doc.insert.return_value = doc
				scripts[doc.name] = doc
				return doc
			return pages[name] if doctype == "Builder Page" else scripts[name]

		db = MagicMock()
		db.get_value.side_effect = lambda dt, filters, field: (
			filters["name"] if filters["name"] in scripts else None
		)
		fields = forms.normalize_fields([{"fieldname": "name"}])
		with patch.object(frappe, "db", db), patch.object(frappe, "get_doc", side_effect=get_doc):
			pending.attach_form_script("A", "Contact", "contact", "#first", fields)
			first = next(iter(scripts.values())).script
			pending.attach_form_script("B", "Contact", "contact", "#second", fields)
			pending.attach_form_script("B", "Contact", "contact", "#second", fields)
		self.assertEqual(len(scripts), 2)
		self.assertEqual(next(iter(scripts.values())).script, first)
		self.assertIn('"input_name": "name"', first)
		self.assertIn('"fieldname": "name_field"', first)
		self.assertNotEqual(pages["A"].append.call_args.args[1], pages["B"].append.call_args.args[1])
		db.commit.assert_not_called()


class TestFormProvisioning(unittest.TestCase):
	def setUp(self):
		self.db = self.enterContext(patch.object(frappe, "db", MagicMock()))
		self.enterContext(patch.object(frappe, "_", side_effect=lambda value: value))
		self.enterContext(patch.object(frappe, "throw", side_effect=ValueError("Rejected form")))
		self.payload = {
			"page_id": "fixture",
			"doctype_name": "Contact",
			"form_selector": "#contact",
			"fields": [{"fieldname": "name", "required": True}],
		}

	def test_missing_page_cannot_report_a_connection(self):
		del self.payload["page_id"]
		with self.assertRaises(ValueError), patch.object(frappe, "get_doc") as get_doc:
			pending.apply_connect_form(self.payload)
		get_doc.assert_not_called()

	def test_page_permission_is_checked_before_provisioning(self):
		doc = MagicMock()
		doc.check_permission.side_effect = frappe.PermissionError("Denied")
		with patch.object(frappe, "get_doc", return_value=doc), self.assertRaises(frappe.PermissionError):
			pending.apply_connect_form(self.payload)
		doc.check_permission.assert_called_once_with("write")
		self.db.exists.assert_not_called()
		doc.insert.assert_not_called()

	def test_provisioning_preserves_required_flags_and_original_names(self):
		self.db.exists.return_value = False
		page = MagicMock()
		created = []

		def get_doc(doctype, name=None):
			if isinstance(doctype, dict):
				created.append(doctype)
				return MagicMock()
			return page

		with (
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(forms, "missing_create_permission", return_value=None),
			patch.object(pending, "attach_form_script") as attach,
		):
			self.assertIn("Form connected", pending.apply_connect_form(self.payload))
		self.assertEqual([doc["doctype"] for doc in created], ["DocType", "Web Form"])
		for doc, key in zip(created, ("fields", "web_form_fields"), strict=True):
			self.assertEqual(doc[key][0]["fieldname"], "name_field")
			self.assertEqual(doc[key][0]["reqd"], 1)
		self.assertEqual(attach.call_args.args[-1][0]["input_name"], "name")

	def test_incompatible_web_form_is_rejected_before_schema_creation(self):
		self.db.exists.side_effect = lambda dt, name: dt == "Web Form"
		web_form = frappe._dict(doc_type="Different", published=1, login_required=0)
		page = MagicMock()
		with (
			patch.object(
				frappe, "get_doc", side_effect=lambda dt, name: page if dt == "Builder Page" else web_form
			),
			patch.object(forms, "missing_create_permission", return_value=None),
			self.assertRaises(ValueError),
		):
			pending.apply_connect_form(self.payload)
		page.insert.assert_not_called()

	def test_reused_schema_and_endpoint_settings_are_validated(self):
		fields = forms.normalize_fields(self.payload["fields"])
		meta = SimpleNamespace(
			fields=[frappe._dict(fields[0])], get_field=lambda key: frappe._dict(fields[0])
		)
		web_form = frappe._dict(
			doc_type="Contact",
			published=1,
			login_required=0,
			allow_multiple=1,
			web_form_fields=[frappe._dict(fields[0])],
		)
		with (
			patch.object(frappe, "get_meta", return_value=meta),
			patch.object(frappe, "get_doc", return_value=web_form),
		):
			pending.validate_form_reuse("Contact", "contact", fields)
			for key, value in (
				("published", 0),
				("login_required", 1),
				("key_required", 1),
				("allow_multiple", 0),
				("web_form_fields", []),
			):
				with self.subTest(key=key), patch.dict(web_form, {key: value}), self.assertRaises(ValueError):
					pending.validate_form_reuse("Contact", "contact", fields)


class TestGeneratedFormScript(unittest.TestCase):
	def run_script(self, html, fields, **options):
		payload = {
			"html": html,
			"script": pending.build_form_script("#contact", "contact", forms.normalize_fields(fields)),
			"action": "submit",
			"expectedCalls": 1,
			**options,
		}
		result = subprocess.run(
			["node", str(Path(__file__).with_name("test_form_script.cjs"))],
			input=json.dumps(payload),
			text=True,
			capture_output=True,
			timeout=15,
		)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_successful_controls_preserve_mapping_checked_and_multiple_values(self):
		html = """<form id="contact">
		<input name="consent" type="checkbox"><input name="plan" type="radio" value="pro" checked>
		<input name="plan" type="radio" value="basic"><input name="Full Name" value="Ada">
		<input name="ignored" disabled value="no"><fieldset disabled><input name="inherited" value="no"></fieldset>
		<input name="choices" type="checkbox" value="one" checked><input name="choices" type="checkbox" value="two">
		<select name="colors" multiple><option selected value="red">Red</option><option selected value="blue">Blue</option>
		<option selected disabled value="disabled">Disabled</option><optgroup disabled><option selected value="group">Group</option></optgroup></select>
		<input name="optional" type="radio" value="omit"><input name="tag" type="checkbox" value="actual" checked>
		<input name="hidden" type="hidden" value="kept"><button>Send</button></form>
		<input form="contact" name="outside" value="associated">"""
		fields = [
			{"fieldname": "name", "input_name": "Full Name"},
			{"fieldname": "consent", "fieldtype": "Check"},
			*[
				{"fieldname": f}
				for f in ("plan", "ignored", "inherited", "optional", "tag", "hidden", "outside")
			],
			{"fieldname": "choices", "multiple": True},
			{"fieldname": "colors", "multiple": True},
		]
		for action in ("click", "submit"):
			with self.subTest(action=action):
				self.run_script(
					html,
					fields,
					action=action,
					loadTwice=True,
					csrf="synthetic-token",
					status="saved",
					expected={
						"name_field": "Ada",
						"consent": 0,
						"plan": "pro",
						"tag": "actual",
						"hidden": "kept",
						"outside": "associated",
						"choices": '["one"]',
						"colors": '["red","blue"]',
					},
				)

	def test_invalid_native_fields_prevent_click_and_keyboard_submission(self):
		for action in ("click", "submit"):
			for control in ('<input name="email" required>', '<input name="email" type="email" value="bad">'):
				with self.subTest(action=action, control=control):
					self.run_script(
						f'<form id="contact">{control}<button>Send</button></form>',
						[{"fieldname": "email"}],
						action=action,
						expectedCalls=0,
					)

	def test_group_and_single_check_requirements_are_enforced(self):
		for multiple in (True, False):
			with self.subTest(multiple=multiple):
				self.run_script(
					'<form id="contact"><input name="consent" type="checkbox"><button>Send</button></form>',
					[{"fieldname": "consent", "fieldtype": "Check", "multiple": multiple, "required": True}],
					expectedCalls=0,
					status="required",
				)

	def test_missing_mapping_or_file_fails_without_positional_fallback(self):
		for control, status in (
			('<input name="different" value="wrong">', "missing"),
			('<input name="email" type="file">', "not supported"),
		):
			with self.subTest(control=control):
				self.run_script(
					f'<form id="contact">{control}<button>Send</button></form>',
					[{"fieldname": "email"}],
					expectedCalls=0,
					status=status,
				)

	def test_failed_post_keeps_values_and_allows_retry(self):
		self.run_script(
			'<form id="contact"><input name="email" value="ada@example.invalid"><button>Send</button></form>',
			[{"fieldname": "email"}],
			fail=True,
			retry=True,
			expectedCalls=2,
			status="could not be saved",
			preserve={"selector": "input", "property": "value", "value": "ada@example.invalid"},
		)

	def test_container_wrapper_uses_native_form_and_does_not_capture_unrelated_button(self):
		html = (
			'<div id="contact"><form><input name="email" value="ok"><button type="button">Auxiliary</button>'
			'<button type="submit">Send</button></form></div>'
		)
		self.run_script(html, [{"fieldname": "email"}], action="submit", expected={"email": "ok"})
		self.run_script(html, [{"fieldname": "email"}], action="click", expectedCalls=0)


if __name__ == "__main__":
	unittest.main()
