"""Unit tests for the server-side markup -> blocks expander (builder/ai/page_writer.py).
Pure-function tests, no DB."""

import unittest

from builder.ai import page_writer as pw


class TestNormalizeStyles(unittest.TestCase):
	def test_fixes_model_css_slips(self):
		out = pw.normalize_styles(
			{
				"justify-content": "spaceBetween",  # kebab name + camelCased value
				"padding": 40,  # bare number → px
				"fontSize": "16",  # bare numeric string → px
				"lineHeight": 1.5,  # unitless — untouched
				"fontFamily": "'Inter', sans-serif",  # bare family only
				"background": "linear-gradient(90deg,#000,#fff)",  # → backgroundImage
				"hover:boxShadow": "0 1px 2px #000",  # state prefix preserved
				"--brand": "#fff",  # custom prop passthrough
				"opacity": None,  # dropped
			}
		)
		self.assertEqual(out["justifyContent"], "space-between")
		self.assertEqual(out["padding"], "40px")
		self.assertEqual(out["fontSize"], "16px")
		self.assertEqual(out["lineHeight"], 1.5)
		self.assertEqual(out["fontFamily"], "Inter")
		self.assertNotIn("background", out)
		self.assertEqual(out["backgroundImage"], "linear-gradient(90deg,#000,#fff)")
		self.assertEqual(out["hover:boxShadow"], "0 1px 2px #000")
		self.assertEqual(out["--brand"], "#fff")
		self.assertNotIn("opacity", out)


class TestConvertNode(unittest.TestCase):
	def test_root_and_child(self):
		root = pw.convert_node(
			{"el": "div", "name": "body", "style": {"display": "flex"}, "c": [{"el": "h1", "text": "Hi"}]},
			is_root=True,
		)
		self.assertEqual(root["blockId"], "root")
		self.assertEqual(root["originalElement"], "body")
		self.assertEqual(root["element"], "div")
		self.assertEqual(root["baseStyles"], {"display": "flex"})
		child = root["children"][0]
		self.assertEqual(child["element"], "h1")
		self.assertEqual(child["innerHTML"], "Hi")
		self.assertNotEqual(child["blockId"], "root")
		self.assertTrue(child["blockId"])

	def test_icon_block(self):
		block = pw.convert_node({"icon": "arrow-right", "style": {"color": "#000"}})
		self.assertEqual(block["element"], "svg")
		self.assertEqual(block["customAttributes"]["data-lucide"], "arrow-right")
		self.assertEqual(block["baseStyles"]["width"], "24px")
		self.assertEqual(block["baseStyles"]["color"], "#000")

	def test_component_reference_and_attrs(self):
		block = pw.convert_node(
			{"el": "div", "component": "Header-1", "attrs": {"href": "/about", "id": "nav"}}
		)
		self.assertEqual(block["extendedFromComponent"], "Header-1")
		self.assertEqual(block["attributes"], {"href": "/about", "id": "nav"})

	def test_repeater_and_bind(self):
		block = pw.convert_node(
			{
				"el": "div",
				"repeat": {
					"data": "features",
					"items": [{"title": "A"}],
					"item": {"el": "div", "c": [{"el": "h3", "bind": {"innerHTML": "title"}}]},
				},
			}
		)
		self.assertTrue(block["isRepeaterBlock"])
		self.assertEqual(block["dataKey"]["key"], "features")
		# the items array is NOT stored on the block — only the template child
		self.assertEqual(len(block["children"]), 1)
		bound = block["children"][0]["children"][0]
		self.assertEqual(bound["dynamicValues"], [{"key": "title", "property": "innerHTML", "type": "key"}])

	def test_bind_attribute(self):
		block = pw.convert_node({"el": "img", "bind": {"src": "photo"}})
		self.assertEqual(block["dynamicValues"], [{"key": "photo", "property": "src", "type": "attribute"}])


class TestRepeaterDataScript(unittest.TestCase):
	def test_builds_shim(self):
		parsed = [
			{
				"el": "div",
				"c": [
					{"el": "section", "repeat": {"data": "stats", "items": [{"n": 1}], "item": {"el": "div"}}}
				],
			}
		]
		script = pw.build_repeater_data_script(parsed)
		self.assertEqual(script, 'data.stats = [{"n":1}]')


class TestBorderBox(unittest.TestCase):
	def test_a_full_width_block_with_side_padding_gets_border_box(self):
		block = pw.convert_node({"el": "section", "style": {"width": "100%", "padding": "80px 48px"}})
		self.assertEqual(block["baseStyles"]["boxSizing"], "border-box")

	def test_vertical_padding_or_a_set_box_sizing_is_left_alone(self):
		for style in (
			{"width": "100%", "padding": "80px 0"},
			{"width": "100%", "padding": "40px", "boxSizing": "content-box"},
			{"width": "50%", "padding": "40px"},
		):
			block = pw.convert_node({"el": "section", "style": style})
			self.assertEqual(block["baseStyles"].get("boxSizing"), style.get("boxSizing"))

	def test_mobile_side_padding_counts(self):
		self.assertTrue(
			pw.needs_border_box({"baseStyles": {"width": "100%"}, "mobileStyles": {"paddingLeft": "20px"}})
		)


class TestExpandPageMarkup(unittest.TestCase):
	def test_strips_fences_and_marks_the_root(self):
		blocks, data_script = pw.expand_page_markup('```\ndiv // body\n  p "Hello"\n```')
		self.assertEqual(len(blocks), 1)
		self.assertEqual(blocks[0]["originalElement"], "body")
		self.assertEqual(blocks[0]["children"][0]["innerHTML"], "Hello")
		self.assertEqual(data_script, "")

	def test_nothing_parses_to_nothing(self):
		self.assertEqual(pw.expand_page_markup(""), ([], ""))
		self.assertEqual(pw.expand_page_markup("!!!"), ([], ""))

	def test_a_bad_line_costs_only_that_line(self):
		errors = []
		blocks, _ = pw.expand_page_markup('div\n  p "Hello"\n  h1 "unclosed\n  p "Bye"', errors=errors)
		self.assertEqual([c["innerHTML"] for c in blocks[0]["children"]], ["Hello", "Bye"])
		self.assertEqual(len(errors), 1)

	def test_wraps_several_top_level_blocks_in_one_root(self):
		blocks, _ = pw.expand_page_markup('section "a"\nsection "b"')
		self.assertEqual(len(blocks[0]["children"]), 2)
		self.assertEqual(blocks[0]["baseStyles"]["flexDirection"], "column")

	def test_static_repeater_items_become_the_data_shim(self):
		blocks, data_script = pw.expand_page_markup('div\n  div repeat(stats=[{"n":1}])\n    p bind(text=n)')
		self.assertTrue(blocks[0]["children"][0]["isRepeaterBlock"])
		self.assertEqual(data_script, 'data.stats = [{"n":1}]')


if __name__ == "__main__":
	unittest.main()
