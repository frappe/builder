import copy
import unittest

from builder.ai.agent.page_changes import (
	describe_block_changes,
	merge_saved_draft,
	round_effects,
	snapshot_blocks,
)


def page(*children) -> dict:
	return {"blockId": "root", "element": "div", "blockName": "body", "children": list(children)}


def block(ref: str, text: str = "", **extra) -> dict:
	return {"blockId": ref, "element": "p", "innerHTML": text, **extra}


def find(tree: dict, ref: str) -> dict:
	return next(child for child in tree["children"] if child["blockId"] == ref)


def run_round(tree: dict, mutate) -> tuple[dict, list]:
	after = copy.deepcopy(tree)
	mutate(after)
	return after, round_effects(snapshot_blocks(tree), snapshot_blocks(after))


def texts(tree: dict) -> list[str]:
	return [child["innerHTML"] for child in tree["children"]]


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


class TestMergeSavedDraft(unittest.TestCase):
	def setUp(self):
		start = page(block("a", "Hi"), block("b", "Yo"))
		self.first_tree, first = run_round(start, lambda tree: find(tree, "a").update(innerHTML="Bob a"))
		self.second_tree, second = run_round(
			self.first_tree, lambda tree: find(tree, "b").update(innerHTML="Bob b")
		)
		self.rounds = [first, second]

	def test_rounds_the_editor_had_not_saved_are_reapplied(self):
		merged = merge_saved_draft(self.first_tree, self.rounds, self.second_tree)
		self.assertEqual(texts(merged), ["Bob a", "Bob b"])

	def test_a_manual_edit_to_a_field_bob_changed_earlier_is_kept(self):
		saved = copy.deepcopy(self.second_tree)
		find(saved, "a")["innerHTML"] = "User a"
		self.assertEqual(texts(merge_saved_draft(saved, self.rounds, self.second_tree)), ["User a", "Bob b"])

	def test_a_manual_edit_to_a_field_of_an_unsaved_round_is_kept(self):
		saved = copy.deepcopy(self.first_tree)
		find(saved, "b")["innerHTML"] = "User b"
		self.assertEqual(texts(merge_saved_draft(saved, self.rounds, self.second_tree)), ["Bob a", "User b"])

	def test_an_unsaved_added_block_is_inserted_and_a_deleted_one_stays_deleted(self):
		start = page(block("a", "Hi"), block("b", "Yo"))
		added_tree, added = run_round(start, lambda tree: tree["children"].append(block("c", "New")))
		later_tree, later = run_round(added_tree, lambda tree: find(tree, "a").update(innerHTML="Bob a"))
		self.assertEqual(texts(merge_saved_draft(start, [added, later], later_tree)), ["Bob a", "Yo", "New"])
		saved = copy.deepcopy(later_tree)
		saved["children"].pop()
		self.assertEqual(texts(merge_saved_draft(saved, [added, later], later_tree)), ["Bob a", "Yo"])
