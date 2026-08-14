from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.query import MAX_PAGE_READS_PER_TURN, run_read_page
from builder.utils import Block


class TestReadPage(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Reference Page",
				"draft_blocks": Block(
					element="div",
					originalElement="body",
					baseStyles={"backgroundColor": "#E6DECA", "fontFamily": "Libre Baskerville"},
					children=[
						Block(
							element="h1",
							innerHTML="Ravens",
							baseStyles={"fontFamily": "Cinzel", "color": "#161412"},
						)
					],
				).as_json(wrap_in_array=True),
			}
		).insert(ignore_if_duplicate=True)

	def ctx(self, page_id="some-other-page", page_read_count=0):
		return SimpleNamespace(page_id=page_id, page_read_count=page_read_count)

	def test_returns_digest_and_structure_for_another_page(self):
		out = run_read_page(self.ctx(), {"page_id": self.page.name})

		self.assertIn("Reference Page", out)
		self.assertIn("READ-ONLY", out)
		self.assertIn("fonts: Libre Baskerville x1, Cinzel x1", out)
		self.assertIn("colors: #E6DECA x1, #161412 x1", out)
		self.assertIn("el: h1", out)

	def test_points_back_to_context_for_the_open_page(self):
		out = run_read_page(self.ctx(page_id=self.page.name), {"page_id": self.page.name})

		self.assertIn("already in your context", out)

	def test_fails_with_a_pointer_for_an_unknown_page(self):
		out = run_read_page(self.ctx(), {"page_id": "no-such-page"})

		self.assertIn("FAILED", out)
		self.assertIn("query_records('Builder Page'", out)

	def test_caps_reads_per_turn(self):
		ctx = self.ctx(page_read_count=MAX_PAGE_READS_PER_TURN)

		self.assertIn("limit reached", run_read_page(ctx, {"page_id": self.page.name}))
