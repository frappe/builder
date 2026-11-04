from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.selectors import design_digest, find_block, walk_blocks


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

	def test_resolves_a_unique_prefix_with_or_without_the_at_sign(self):
		page = {"blockId": "root", "children": [text("k3x9abcde"), text("k3y1fghij")]}
		self.assertEqual(find_block(page, "@k3x9")["blockId"], "k3x9abcde")
		self.assertEqual(find_block(page, "k3y1")["blockId"], "k3y1fghij")

	def test_an_ambiguous_or_too_short_prefix_resolves_nothing(self):
		page = {"blockId": "root", "children": [text("k3x9abcde"), text("k3x9fghij")]}
		self.assertIsNone(find_block(page, "k3x9"))
		self.assertIsNone(find_block(page, "k3"))


STYLED_PAGE = {
	"blockId": "root",
	"element": "body",
	"baseStyles": {"backgroundColor": "#E6DECA", "fontFamily": "Libre Baskerville"},
	"children": [
		{
			"blockId": "hero",
			"element": "section",
			"blockName": "hero",
			"baseStyles": {"backgroundColor": "#E6DECA"},
			"children": [
				text("title", "h1", "Ravens", baseStyles={"fontFamily": "Cinzel", "color": "#161412"}),
				text("cta", "a", "Send word", baseStyles={"color": "#161412", "borderRadius": "2px"}),
			],
		},
		{"blockId": "footer", "element": "section", "children": []},
	],
}


class TestDesignDigest(FrappeTestCase):
	def test_counts_fonts_colors_and_radii_across_the_tree(self):
		digest = design_digest(STYLED_PAGE)

		self.assertIn("fonts: Libre Baskerville x1 (body), Cinzel x1 (h1)", digest)
		self.assertIn("colors: #E6DECA x2, #161412 x2", digest)
		self.assertIn("radii: 2px x1", digest)

	def test_states_each_fonts_role_elements_and_sizes(self):
		# The working face vs a one-off accent must be tellable apart from the
		# digest alone: 'Newsreader x1' with no role got promoted to every heading.
		page = {
			"blockId": "root",
			"element": "body",
			"children": [
				text("a", "p", "body", baseStyles={"fontFamily": "Inter", "fontSize": "16px"}),
				text("b", "h2", "head", baseStyles={"fontFamily": "Inter", "fontSize": "20px"}),
				text("c", "p", "hero", baseStyles={"fontFamily": "Newsreader", "fontSize": "48px"}),
			],
		}

		digest = design_digest(page)

		self.assertIn("Inter x2 (p/h2 at 16px, 20px)", digest)
		self.assertIn("Newsreader x1 (p at 48px)", digest)

	def test_lists_top_level_sections_in_order(self):
		self.assertIn("sections: section(hero) > section", design_digest(STYLED_PAGE))

	def test_reports_an_unstyled_tree(self):
		self.assertEqual(design_digest({"blockId": "root", "children": []}), "(no styles set)")
