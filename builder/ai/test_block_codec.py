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

		self.assertEqual(out, {"icon": "star", "ref": "abc123", "name": "Star", "style": {"display": "flex"}})

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

	def test_surfaces_a_visibility_condition_as_a_visible_binding(self):
		cases = [
			({"key": "show_offer", "comesFrom": "dataScript"}, "show_offer"),
			({"key": "open", "comesFrom": "props"}, "props.open"),
			({"key": "live", "comesFrom": "componentData"}, "component.live"),
			("legacy_key", "legacy_key"),
		]
		for condition, visible in cases:
			out = BlockCodec.compress(block(visibilityCondition=condition))

			self.assertEqual(out["bind"]["visible"], visible)
		self.assertNotIn("bind", BlockCodec.compress(block(visibilityCondition={"key": ""})))

	def test_tolerates_null_children(self):
		self.assertEqual(BlockCodec.compress({"element": "p", "children": None}), {"el": "p"})


class TestStripFences(FrappeTestCase):
	def test_strips_a_fence(self):
		self.assertEqual(BlockCodec.strip_fences("```\nsection\n```"), "section")


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
