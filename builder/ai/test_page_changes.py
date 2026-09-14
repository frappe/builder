import unittest

from builder.ai.agent.page_changes import describe_block_changes


def page(*children) -> dict:
	return {"blockId": "root", "element": "div", "blockName": "body", "children": list(children)}


def block(ref: str, text: str = "", **extra) -> dict:
	return {"blockId": ref, "element": "p", "innerHTML": text, **extra}


class TestDescribeBlockChanges(unittest.TestCase):
	def test_identical_pages_have_no_changes(self):
		self.assertEqual(
			describe_block_changes(page(block("a", "Hi")), page(block("a", "Hi", classes=[]))), []
		)

	def test_text_change_names_the_block_and_both_texts(self):
		lines = describe_block_changes(page(block("a", "Hi")), page(block("a", "<b>Hello</b>")))
		self.assertEqual(lines, ["<p> (ref a): text 'Hi' -> 'Hello'"])

	def test_added_and_removed_blocks_report_only_the_subtree_root(self):
		before = page(block("a", "Hi", children=[block("a1")]))
		after = page(block("b", "New", children=[block("b1")]))
		self.assertEqual(
			sorted(describe_block_changes(before, after)),
			["added <p> (ref b) inside body", "removed <p> (ref a)"],
		)

	def test_move_is_reported(self):
		before = page({"blockId": "box", "element": "div", "children": []}, block("a"))
		after = page({"blockId": "box", "element": "div", "children": [block("a")]})
		self.assertIn("<p> (ref a): moved inside <div>", describe_block_changes(before, after))
