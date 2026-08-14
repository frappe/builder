from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.selectors import (
	block_text,
	find_block,
	is_text_block,
	match_block,
	render_skeleton,
	walk_blocks,
)


def text(block_id, tag="p", copy="", **overrides):
	return {"blockId": block_id, "element": tag, "innerHTML": copy, "children": [], **overrides}


PAGE = {
	"blockId": "root",
	"element": "body",
	"children": [
		{
			"blockId": "hero",
			"element": "section",
			"blockName": "Hero",
			"children": [text("title", "h1", "A study in permanence.")],
		},
		text("cta", "a", "Book", classes=["button"]),
	],
}


class TestWalking(FrappeTestCase):
	def test_yields_every_block_with_its_depth(self):
		self.assertEqual(
			[(b["blockId"], d) for b, d in walk_blocks(PAGE)],
			[("root", 0), ("hero", 1), ("title", 2), ("cta", 1)],
		)

	def test_yields_nothing_for_a_value_that_is_not_a_block(self):
		self.assertEqual(list(walk_blocks("nope")), [])

	def test_finds_a_block_by_id(self):
		self.assertEqual(find_block(PAGE, "title")["element"], "h1")

	def test_returns_nothing_for_an_unknown_id(self):
		self.assertIsNone(find_block(PAGE, "missing"))


class TestTextBlocks(FrappeTestCase):
	def test_reads_the_text_of_a_block(self):
		self.assertEqual(block_text(text("a", copy="  Hello  ")), "Hello")

	def test_a_leaf_with_copy_is_a_text_block(self):
		self.assertTrue(is_text_block(text("a", copy="Hello")))

	def test_a_container_is_not_a_text_block(self):
		self.assertFalse(is_text_block(PAGE["children"][0]))

	def test_an_empty_block_is_not_a_text_block(self):
		self.assertFalse(is_text_block(text("a")))

	def test_an_svg_blob_is_not_copy(self):
		self.assertFalse(is_text_block(text("a", "div", "<svg viewBox='0 0 1 1'/>")))


class TestSkeleton(FrappeTestCase):
	def test_indents_by_depth_and_names_each_block(self):
		self.assertEqual(
			render_skeleton(PAGE).split("\n"),
			[
				"root body",
				"  hero section (Hero)",
				'    title h1 "A study in permanence."',
				'  cta a "Book"',
			],
		)

	def test_truncates_a_long_preview(self):
		out = render_skeleton(text("a", "p", "x" * 80), max_text=10)

		self.assertIn('"' + "x" * 9 + '…"', out)


class TestMatching(FrappeTestCase):
	def test_matches_on_element(self):
		self.assertTrue(match_block(text("a", "h1", "Hi"), element="H1"))
		self.assertFalse(match_block(text("a", "h1", "Hi"), element="p"))

	def test_matches_on_contained_text(self):
		self.assertTrue(match_block(text("a", "p", "Book a table"), contains="TABLE"))
		self.assertFalse(match_block(text("a", "p", "Book a table"), contains="menu"))

	def test_matches_on_class(self):
		self.assertTrue(match_block(text("a", classes=["button"]), class_name="button"))
		self.assertFalse(match_block(text("a"), class_name="button"))

	def test_matches_text_blocks_only(self):
		self.assertFalse(match_block(PAGE["children"][0], text_only=True))

	def test_filters_are_combined(self):
		block = text("a", "p", "Book a table")

		self.assertTrue(match_block(block, element="p", contains="book"))
		self.assertFalse(match_block(block, element="h1", contains="book"))

	def test_matches_anything_without_filters(self):
		self.assertTrue(match_block(text("a")))
