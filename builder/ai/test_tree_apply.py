"""Unit tests for the mutating WorkingTree (builder/ai/agent/tree.py).

Headless agents have no browser, so apply() performs block edits on the
serialized tree itself. These pin the Python applier to the frontend behaviour
in toolDispatch.applyBlockUpdate / applyToolOperation so the two can't drift.
"""

import unittest

from builder.ai.agent.tree import WorkingTree


def sample_root() -> dict:
	return {
		"blockId": "root",
		"element": "div",
		"children": [
			{
				"blockId": "hero",
				"element": "section",
				"baseStyles": {"padding": "40px", "backgroundColor": "#fff"},
				"attributes": {"title": "Hero"},
				"children": [
					{"blockId": "h1", "element": "h1", "innerHTML": "Hello"},
					{"blockId": "cta", "element": "button", "innerHTML": "Go"},
				],
			},
			{"blockId": "footer", "element": "footer", "children": []},
		],
	}


class TestMutatingUpdate(unittest.TestCase):
	def setUp(self):
		self.root = sample_root()
		self.tree = WorkingTree(self.root, mutating=True)

	def test_styles_merge_and_normalize(self):
		msg = self.tree.apply(
			"update_block",
			{"block_id": "hero", "base_styles": {"padding": 64, "justifyContent": "spaceBetween"}},
		)
		self.assertIn("Applied to block hero", msg)
		hero = self.tree.resolve("hero")
		# merged (backgroundColor kept), normalized (px added, keyword fixed)
		self.assertEqual(hero["baseStyles"]["padding"], "64px")
		self.assertEqual(hero["baseStyles"]["backgroundColor"], "#fff")
		self.assertEqual(hero["baseStyles"]["justifyContent"], "space-between")

	def test_attributes_split_standard_vs_custom(self):
		self.tree.apply(
			"update_block",
			{"block_id": "cta", "attributes": {"href": "/buy", "data-test": "cta", "id": "buy-btn"}},
		)
		cta = self.tree.resolve("cta")
		self.assertEqual(cta["attributes"], {"href": "/buy"})  # standard attr
		self.assertEqual(cta["customAttributes"], {"data-test": "cta", "id": "buy-btn"})

	def test_html_wins_over_text_and_classes_replace(self):
		self.tree.apply(
			"update_block",
			{"block_id": "h1", "inner_text": "plain", "inner_html": "<em>rich</em>", "classes": ["x"]},
		)
		h1 = self.tree.resolve("h1")
		self.assertEqual(h1["innerHTML"], "<em>rich</em>")
		self.assertEqual(h1["classes"], ["x"])

	def test_update_blocks_uniform_and_patches(self):
		msg = self.tree.apply(
			"update_blocks", {"block_ids": ["h1", "cta", "ghost"], "base_styles": {"color": "#111"}}
		)
		self.assertIn("Applied to 2 of 3", msg)
		self.assertIn("ghost", msg)
		self.assertEqual(self.tree.resolve("h1")["baseStyles"]["color"], "#111")
		self.tree.apply(
			"update_blocks",
			{"patches": [{"block_id": "h1", "inner_text": "Uno"}, {"block_id": "cta", "inner_text": "Dos"}]},
		)
		self.assertEqual(self.tree.resolve("h1")["innerHTML"], "Uno")
		self.assertEqual(self.tree.resolve("cta")["innerHTML"], "Dos")

	def test_bind_merges_replaces_and_unbinds(self):
		self.tree.apply("update_block", {"block_id": "h1", "bind": {"innerHTML": "title", "src": "image"}})
		h1 = self.tree.resolve("h1")
		self.assertIn({"key": "title", "property": "innerHTML", "type": "key"}, h1["dynamicValues"])
		self.assertIn({"key": "image", "property": "src", "type": "attribute"}, h1["dynamicValues"])
		# re-bind replaces (no duplicate property entries); "text" aliases innerHTML
		self.tree.apply("update_block", {"block_id": "h1", "bind": {"text": "name"}})
		h1 = self.tree.resolve("h1")
		content = [dv for dv in h1["dynamicValues"] if dv["property"] == "innerHTML"]
		self.assertEqual(content, [{"key": "name", "property": "innerHTML", "type": "key"}])
		# null unbinds
		self.tree.apply("update_block", {"block_id": "h1", "bind": {"src": None}})
		props = [dv["property"] for dv in self.tree.resolve("h1")["dynamicValues"]]
		self.assertNotIn("src", props)

	def test_add_repeater_with_bound_template(self):
		self.tree.apply(
			"add_block",
			{
				"parent_block_id": "hero",
				"block": {
					"el": "div",
					"repeat": {
						"data": "products",
						"item": {"el": "div", "c": [{"el": "h3", "bind": {"innerHTML": "title"}}]},
					},
				},
			},
		)
		repeater = self.tree.resolve("hero")["children"][-1]
		self.assertTrue(repeater["isRepeaterBlock"])
		self.assertEqual(repeater["dataKey"]["key"], "products")
		template_heading = repeater["children"][0]["children"][0]
		self.assertEqual(
			template_heading["dynamicValues"], [{"key": "title", "property": "innerHTML", "type": "key"}]
		)

	def test_binding_prefixes_are_normalized(self):
		# The renderer resolves keys relative to their context: 'data.'/'item.' prefixes
		# (which models habitually write) would silently break resolution.
		self.tree.apply(
			"add_block",
			{
				"parent_block_id": "hero",
				"block": {
					"el": "div",
					"repeat": {
						"data": "data.products",
						"item": {"el": "img", "bind": {"src": "item.image"}},
					},
				},
			},
		)
		repeater = self.tree.resolve("hero")["children"][-1]
		self.assertEqual(repeater["dataKey"]["key"], "products")
		self.assertEqual(repeater["children"][0]["dynamicValues"][0]["key"], "image")
		self.tree.apply("update_block", {"block_id": "cta", "bind": {"innerHTML": "item.title"}})
		self.assertEqual(self.tree.resolve("cta")["dynamicValues"][0]["key"], "title")

	def test_expression_bind_keys_are_rejected(self):
		msg = self.tree.apply(
			"update_block", {"block_id": "cta", "bind": {"innerHTML": "in_stock ? 'In Stock' : 'Out'"}}
		)
		self.assertIn("FAILED", msg)
		self.assertIn("data script", msg)
		self.assertNotIn("dynamicValues", self.tree.resolve("cta"))
		msg = self.tree.apply(
			"update_blocks",
			{
				"patches": [
					{"block_id": "h1", "inner_text": "ok"},
					{"block_id": "cta", "bind": {"innerHTML": "'$' + price"}},
				]
			},
		)
		self.assertIn("BAD BIND", msg)
		self.assertEqual(self.tree.resolve("h1")["innerHTML"], "ok")  # good patch still applied

	def test_repeater_via_bind_is_rejected(self):
		msg = self.tree.apply("update_block", {"block_id": "hero", "bind": {"repeat": "events"}})
		self.assertIn("FAILED", msg)
		self.assertIn("add_block", msg)
		self.assertNotIn("dynamicValues", self.tree.resolve("hero"))

	def test_validating_mode_does_not_mutate(self):
		tree = WorkingTree(sample_root())  # mutating=False (editor)
		msg = tree.apply("update_block", {"block_id": "hero", "base_styles": {"padding": "1px"}})
		self.assertIn("Applied to block hero", msg)
		self.assertEqual(tree.resolve("hero")["baseStyles"]["padding"], "40px")


class TestMutatingStructure(unittest.TestCase):
	def setUp(self):
		self.tree = WorkingTree(sample_root(), mutating=True)

	def child_ids(self, ref: str) -> list:
		return [c["blockId"] for c in self.tree.resolve(ref)["children"]]

	def test_add_assigns_ref_and_position(self):
		msg = self.tree.apply(
			"add_block",
			{"parent_block_id": "hero", "block": {"el": "p", "text": "Sub"}, "after_block_id": "h1"},
		)
		self.assertIn("Added block", msg)
		self.assertIn("under hero", msg)
		ids = self.child_ids("hero")
		self.assertEqual(len(ids), 3)
		new_ref = ids[1]  # right after h1
		self.assertNotIn(new_ref, ("h1", "cta"))
		# the returned ref is usable for a follow-up edit
		self.assertIn(new_ref, msg)
		self.assertIn("Applied", self.tree.apply("update_block", {"block_id": new_ref, "inner_text": "x"}))

	def test_add_at_index_and_append(self):
		self.tree.apply("add_block", {"parent_block_id": "hero", "block": {"el": "span"}, "index": 0})
		self.assertEqual(self.tree.resolve("hero")["children"][0]["element"], "span")
		self.tree.apply("add_block", {"parent_block_id": "hero", "block": {"el": "a"}})
		self.assertEqual(self.tree.resolve("hero")["children"][-1]["element"], "a")

	def test_add_converts_yaml_vocab(self):
		self.tree.apply(
			"add_block",
			{
				"parent_block_id": "footer",
				"block": {"el": "div", "style": {"padding": 16}, "component": "shared-header"},
			},
		)
		block = self.tree.resolve("footer")["children"][0]
		self.assertEqual(block["baseStyles"]["padding"], "16px")
		self.assertEqual(block["extendedFromComponent"], "shared-header")

	def test_move_honors_position_and_rejects_cycles(self):
		self.tree.apply("move_block", {"block_id": "cta", "new_parent_block_id": "root", "index": 0})
		self.assertEqual(self.child_ids("root")[0], "cta")
		self.assertNotIn("cta", self.child_ids("hero"))
		msg = self.tree.apply("move_block", {"block_id": "root", "new_parent_block_id": "hero"})
		self.assertIn("FAILED", msg)

	def test_remove_detaches(self):
		self.tree.apply("remove_block", {"block_id": "h1"})
		self.assertIsNone(self.tree.resolve("h1"))
		self.assertEqual(self.child_ids("hero"), ["cta"])


if __name__ == "__main__":
	unittest.main()
