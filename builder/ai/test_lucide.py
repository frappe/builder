from frappe.tests.utils import FrappeTestCase

from builder.ai.lucide import kebab, lucide_svg


class TestLucide(FrappeTestCase):
	def test_bakes_a_wrapper_filling_svg(self):
		svg = lucide_svg("play")

		self.assertIn('width="100%"', svg)
		self.assertIn('height="100%"', svg)
		self.assertIn('stroke="currentColor"', svg)
		self.assertNotIn("class=", svg)

	def test_accepts_pascal_case_and_custom_stroke(self):
		svg = lucide_svg("ArrowRight", stroke_width=1.5)

		self.assertIn('stroke-width="1.5"', svg)

	def test_unknown_names_return_empty(self):
		self.assertEqual(lucide_svg("no-such-icon-xyz"), "")

	def test_kebab(self):
		self.assertEqual(kebab("ArrowRight"), "arrow-right")
		self.assertEqual(kebab("building 2"), "building-2")
