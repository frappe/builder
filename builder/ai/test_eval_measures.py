from frappe.tests.utils import FrappeTestCase

from builder.ai.eval.measures import PageMeasure, changed_blocks, dead_styles, escapes_text, overflows_width


def block(block_id, el="div", children=(), **fields):
	return {"blockId": block_id, "element": el, "children": list(children), **fields}


class TestEvalMeasures(FrappeTestCase):
	def test_a_box_inside_a_text_element_escapes_it(self):
		self.assertTrue(escapes_text(block("p", "p", [block("t", "div", innerHTML="Hi")])))
		self.assertFalse(escapes_text(block("p", "p", [block("s", "span")])))

	def test_block_fields_and_broken_keys_in_styles_are_dead(self):
		self.assertEqual(
			dead_styles(block("a", baseStyles={"text": "x", "color": "red", "hover:href": "/"})), 2
		)

	def test_absolute_children_of_an_unpositioned_parent_are_pinned(self):
		photo = block("img", "img", baseStyles={"position": "absolute"})
		root = block("root", children=[block("hero", children=[photo])])
		self.assertEqual(PageMeasure(root).pinned_absolute(), 1)
		root["children"][0]["baseStyles"] = {"position": "relative"}
		self.assertEqual(PageMeasure(root).pinned_absolute(), 0)

	def test_full_width_with_side_padding_overflows(self):
		self.assertTrue(overflows_width(block("s", baseStyles={"width": "100%", "padding": "80px 48px"})))
		self.assertFalse(overflows_width(block("s", baseStyles={"width": "100%", "padding": "80px 0"})))

	def test_counts_added_removed_and_altered_blocks(self):
		before = block("root", children=[block("a", innerHTML="x"), block("b")])
		after = block("root", children=[block("a", innerHTML="y"), block("c")])
		self.assertEqual(changed_blocks(before, after), 3)
		self.assertEqual(changed_blocks(before, before), 0)
