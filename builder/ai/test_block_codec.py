import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.block_codec import BlockCodec


def block(**overrides):
	return {
		"element": "div",
		"blockId": "abc123",
		"blockName": "Hero",
		"baseStyles": {"display": "flex"},
		"attributes": {"src": "/files/a.png"},
		"customAttributes": {"data-track": "hero"},
		"children": [],
		**overrides,
	}


class TestCompress(FrappeTestCase):
	def test_renames_the_editor_fields(self):
		out = BlockCodec.compress(block())

		self.assertEqual(out["el"], "div")
		self.assertEqual(out["ref"], "abc123")
		self.assertEqual(out["name"], "Hero")
		self.assertEqual(out["style"], {"display": "flex"})

	def test_merges_custom_attributes_into_attrs(self):
		out = BlockCodec.compress(block())

		self.assertEqual(out["attrs"], {"src": "/files/a.png", "data-track": "hero"})

	def test_drops_empty_fields(self):
		out = BlockCodec.compress({"element": "div"})

		self.assertEqual(out, {"el": "div"})

	def test_compresses_children(self):
		out = BlockCodec.compress(block(children=[block(blockId="child", blockName="Inner")]))

		self.assertEqual(out["c"][0]["ref"], "child")

	def test_collapses_a_baked_icon_back_to_its_name(self):
		icon = block(
			customAttributes={"data-lucide": "star"},
			innerHTML="<svg>…</svg>",
			blockName="Star",
		)
		out = BlockCodec.compress(icon)

		self.assertEqual(out, {"icon": "star", "name": "Star", "style": {"display": "flex"}})

	def test_keeps_tablet_styles_shallow_on_a_simple_task(self):
		nested = block(children=[block(children=[block(tabletStyles={"gap": "4px"})])])
		out = BlockCodec.compress(nested, task_tier="simple")

		self.assertNotIn("t_style", out["c"][0]["c"][0])

	def test_ignores_a_value_that_is_not_a_block(self):
		self.assertEqual(BlockCodec.compress("nope"), "nope")

	def test_surfaces_repeaters_and_bindings(self):
		repeater = block(
			isRepeaterBlock=True,
			dataKey={"key": "products", "property": "innerHTML", "type": "key"},
			dynamicValues=[
				{"key": "title", "property": "innerHTML", "type": "key"},
				{"key": "image", "property": "src", "type": "attribute"},
			],
		)
		out = BlockCodec.compress(repeater)

		self.assertEqual(out["repeat"], {"data": "products"})
		self.assertEqual(out["bind"], {"innerHTML": "title", "src": "image"})

	def test_tolerates_null_children(self):
		self.assertEqual(BlockCodec.compress({"element": "p", "children": None}), {"el": "p"})


class TestExpand(FrappeTestCase):
	def test_restores_the_editor_fields(self):
		out = BlockCodec.expand({"el": "section", "name": "Hero", "text": "Hi"})

		self.assertEqual(out["element"], "section")
		self.assertEqual(out["blockName"], "Hero")
		self.assertEqual(out["innerHTML"], "Hi")

	def test_splits_standard_and_custom_attributes(self):
		out = BlockCodec.expand({"attrs": {"src": "/a.png", "data-x": "1"}})

		self.assertEqual(out["attributes"], {"src": "/a.png"})
		self.assertEqual(out["customAttributes"], {"data-x": "1"})

	def test_defaults_the_element_to_div(self):
		self.assertEqual(BlockCodec.expand({})["element"], "div")

	def test_rebuilds_an_icon(self):
		out = BlockCodec.expand({"icon": "star"})

		self.assertEqual(out["element"], "svg")
		self.assertEqual(out["customAttributes"], {"data-lucide": "star"})

	def test_round_trips_a_block(self):
		original = block(children=[block(blockId="child")])
		out = BlockCodec.expand(BlockCodec.compress(original))

		self.assertEqual(out["element"], original["element"])
		self.assertEqual(out["baseStyles"], original["baseStyles"])
		self.assertEqual(out["attributes"], original["attributes"])
		self.assertEqual(out["children"][0]["blockName"], "Hero")


class TestParsing(FrappeTestCase):
	def test_strips_a_yaml_fence(self):
		self.assertEqual(BlockCodec.strip_fences("```yaml\nel: div\n```"), "el: div")

	def test_parses_a_block_and_names_the_root(self):
		out = BlockCodec.parse_blocks("el: section")

		self.assertEqual(out["element"], "section")
		self.assertEqual(out["blockId"], "root")

	def test_parses_the_first_block_of_a_list(self):
		self.assertEqual(BlockCodec.parse_blocks("- el: main")["element"], "main")

	def test_rejects_content_that_is_not_a_block(self):
		with self.assertRaises(ValueError):
			BlockCodec.parse_blocks("just a sentence")

	def test_reads_the_block_id_out_of_a_context(self):
		context = frappe.as_json([{"blockId": "abc123"}])

		self.assertEqual(BlockCodec.extract_block_id(context), "abc123")

	def test_returns_no_block_id_for_junk(self):
		self.assertIsNone(BlockCodec.extract_block_id("not json"))


class TestStripContext(FrappeTestCase):
	def test_returns_only_the_text_for_a_rewrite(self):
		context = frappe.as_json({"innerHTML": "Old headline"})

		self.assertEqual(BlockCodec.strip_context(context, "simple", "rewrite_text"), "Old headline")

	def test_returns_only_the_image_for_a_replace(self):
		context = frappe.as_json({"attributes": {"src": "/a.png", "alt": "A"}})
		out = BlockCodec.strip_context(context, "simple", "replace_image")

		self.assertIn("/a.png", out)

	def test_compresses_the_block_for_anything_else(self):
		out = BlockCodec.strip_context(frappe.as_json(block()), "complex")

		self.assertIn("ref: abc123", out)

	def test_passes_through_content_that_is_not_json(self):
		self.assertEqual(BlockCodec.strip_context("plain", "simple"), "plain")


class TestHelpers(FrappeTestCase):
	def test_truncates_a_long_value(self):
		out = BlockCodec.truncate_for_log("x" * 20, limit=10)

		self.assertTrue(out.startswith("x" * 10))
		self.assertIn("truncated 10 chars", out)

	def test_leaves_a_short_value_alone(self):
		self.assertEqual(BlockCodec.truncate_for_log("short", limit=10), "short")

	def test_accepts_an_image_data_url(self):
		data = "data:image/png;base64,AAAA"

		self.assertEqual(BlockCodec.validate_image_data(data), data)

	def test_rejects_data_that_is_not_an_image(self):
		with self.assertRaises(frappe.ValidationError):
			BlockCodec.validate_image_data("https://example.com/a.png")

	def test_rejects_an_image_that_is_too_large(self):
		with self.assertRaises(frappe.ValidationError):
			BlockCodec.validate_image_data("data:image/png;base64," + "A" * (7 * 1024 * 1024))
