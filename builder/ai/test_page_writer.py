"""Unit tests for the server-side YAML→blocks expander (builder/ai/page_writer.py).

Pure-function tests (no DB): they pin the port to the frontend behaviour in
convertYAMLtoBlock / normalizeStyles / buildRepeaterDataScript so the two paths
can't silently drift.
"""

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


class TestConvertYamlBlock(unittest.TestCase):
	def test_root_and_child(self):
		root = pw.convert_yaml_block(
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
		block = pw.convert_yaml_block({"icon": "arrow-right", "style": {"color": "#000"}})
		self.assertEqual(block["element"], "svg")
		self.assertEqual(block["customAttributes"]["data-lucide"], "arrow-right")
		self.assertEqual(block["baseStyles"]["width"], "24px")
		self.assertEqual(block["baseStyles"]["color"], "#000")

	def test_component_reference_and_attrs(self):
		block = pw.convert_yaml_block(
			{"el": "div", "component": "Header-1", "attrs": {"href": "/about", "id": "nav"}}
		)
		self.assertEqual(block["extendedFromComponent"], "Header-1")
		self.assertEqual(block["attributes"], {"href": "/about", "id": "nav"})

	def test_repeater_and_bind(self):
		block = pw.convert_yaml_block(
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
		block = pw.convert_yaml_block({"el": "img", "bind": {"src": "photo"}})
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


class TestExpandPageYaml(unittest.TestCase):
	def test_strips_fences_and_requires_el(self):
		yaml_text = "```yaml\nel: div\nname: body\nc:\n  - el: p\n    text: Hello\n```"
		blocks, data_script = pw.expand_page_yaml(yaml_text)
		self.assertEqual(len(blocks), 1)
		self.assertEqual(blocks[0]["originalElement"], "body")
		self.assertEqual(blocks[0]["children"][0]["innerHTML"], "Hello")
		self.assertEqual(data_script, "")

	def test_rejects_non_block(self):
		self.assertEqual(pw.expand_page_yaml("just a string"), ([], ""))
		self.assertEqual(pw.expand_page_yaml("- foo: 1"), ([], ""))


if __name__ == "__main__":
	unittest.main()
