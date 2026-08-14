from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.query import (
	MAX_PAGE_READS_PER_TURN,
	resolve_page_reference,
	run_read_page,
)
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


class TestResolvePageReference(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Raven Chat",
				"route": "raven-chat",
				"draft_blocks": Block(element="div", originalElement="body").as_json(wrap_in_array=True),
			}
		).insert(ignore_if_duplicate=True)

	def test_resolves_a_doc_id(self):
		self.assertEqual(resolve_page_reference(self.page.name), (self.page.name, ""))

	def test_resolves_a_route_with_or_without_slash(self):
		self.assertEqual(resolve_page_reference("raven-chat")[0], self.page.name)
		self.assertEqual(resolve_page_reference("/raven-chat")[0], self.page.name)

	def test_resolves_a_page_title(self):
		self.assertEqual(resolve_page_reference("Raven Chat")[0], self.page.name)

	def test_resolves_an_editor_url_of_this_site(self):
		host = frappe.utils.get_url()
		builder_path = frappe.conf.builder_path or "builder"

		page_id, why = resolve_page_reference(f"{host}/{builder_path}/page/{self.page.name}")

		self.assertEqual((page_id, why), (self.page.name, ""))

	def test_resolves_a_published_url_of_this_site(self):
		self.assertEqual(resolve_page_reference(f"{frappe.utils.get_url()}/raven-chat")[0], self.page.name)

	def test_rejects_a_url_on_another_host(self):
		page_id, why = resolve_page_reference("https://example.com/raven-chat")

		self.assertIsNone(page_id)
		self.assertIn("not this site", why)

	def test_fails_helpfully_for_an_unknown_reference(self):
		page_id, why = resolve_page_reference("no-such-thing")

		self.assertIsNone(page_id)
		self.assertIn("no-such-thing", why)


class TestOpenPageContext(FrappeTestCase):
	def test_names_the_open_page_and_nothing_else(self):
		from builder.ai.agent.loop import AgentRunner

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Context Page",
				"draft_blocks": Block(element="div", originalElement="body").as_json(wrap_in_array=True),
			}
		).insert(ignore_if_duplicate=True)
		runner = AgentRunner("hi", model="m", api_key="k", page_id=page.name)

		out = runner.build_open_page_context()

		self.assertIn(f"id {page.name}", out)
		self.assertIn("'Context Page'", out)
		self.assertIn("draft", out)
		# The site's URL and structure are DISCOVERED via the read tools, never pre-baked.
		self.assertNotIn(frappe.utils.get_url(), out)
