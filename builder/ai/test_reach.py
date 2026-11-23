"""A run whose hosting app withholds every tool that searches the site (run_python, query_records, get_document)
hears how far an edit on the open page reaches: the site's other pages, and how many pages, and how many live,
each component on the open page is embedded on. His asking rules for an edit past the page quote those counts in
a scope question, and he has no other way to get them. frappe.page's own site withholds all three."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import page_writer
from builder.ai.agent import reach
from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.tree import WorkingTree
from builder.builder.tests.hosting_hooks import hosting_hooks, page_tools, search_tools, without_save_hooks


class TestReach(FrappeTestCase):
	def setUp(self):
		super().setUp()
		# Builder's own pages, whatever routes or states an installed host refuses on save
		self.enterContext(without_save_hooks())
		self.tag = frappe.generate_hash(length=6)
		self.nav, self.hero, self.lone = (self.component(label) for label in ("Nav", "Hero", "Lone"))
		self.open_page = self.page("Home", self.nav, self.hero, publish="live")
		self.draft = self.page("Draft", self.nav)
		self.staged = self.page("Staged", self.nav, publish="staging")
		self.lone_page = self.page("Lone", self.lone)

	def component(self, label: str) -> str:
		block = {"blockId": "root", "element": "div", "children": []}
		doc = {"doctype": "Builder Component", "component_name": label, "block": frappe.as_json(block)}
		return frappe.get_doc(doc).insert().name

	def page(self, title: str, *components: str, publish: str = "") -> str:
		instances = [
			{"blockId": f"use{i}", "element": "div", "extendedFromComponent": component, "children": []}
			for i, component in enumerate(components)
		]
		root = {"blockId": "root", "element": "div", "originalElement": "body", "children": instances}
		doc = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": title,
				"route": f"reach-{self.tag}-{title.lower()}",
				"draft_blocks": frappe.as_json([root]),
			}
		).insert()
		if publish == "live":
			doc.publish()
		elif publish == "staging":
			doc.publish_to_staging()
		return doc.name

	def context(self, page_id: str, *hooks) -> str:
		with hosting_hooks(builder_agent_tools=list(hooks or [page_tools])):
			runner = AgentRunner("rename the brand", model="m", api_key="k", page_id=page_id)
		runner.tree = WorkingTree(page_writer.load_page_root(page_id))
		return runner.build_withheld_context()

	def test_he_hears_how_many_pages_and_live_pages_each_component_is_on(self):
		with patch.object(reach, "MAX_PAGES", 10_000):
			context = self.context(self.open_page)

		self.assertIn(f"{self.nav} on 3 pages (1 live, 1 staging)", context)
		self.assertIn(f"{self.hero} on this page only", context)
		self.assertIn(f"'Draft' (id {self.draft}, /reach-{self.tag}-draft, draft)", context)
		self.assertIn(f"'Staged' (id {self.staged}, /reach-{self.tag}-staged, staging)", context)
		self.assertNotIn(f"id {self.open_page}", context)

	def test_a_page_whose_components_are_nowhere_else_reaches_no_other_page(self):
		with patch.object(reach, "MAX_PAGES", 10_000):
			context = self.context(self.lone_page)

		self.assertIn(reach.ALL_HERE, context)
		self.assertNotIn("Where the components on this page are embedded", context)

	def test_the_sites_only_page_has_no_scope_to_ask_about(self):
		get_list = frappe.get_list

		def only_the_open_page(doctype, *args, **kwargs):
			return get_list(doctype, *args, filters={"name": self.open_page}, **kwargs)

		with patch.object(reach.frappe, "get_list", only_the_open_page):
			context = self.context(self.open_page)

		self.assertIn(reach.ONLY_PAGE, context)
		self.assertNotIn("Besides this page", context)

	def test_past_the_page_limit_he_names_the_scopes_without_numbers(self):
		with patch.object(reach, "MAX_PAGES", 2):
			context = self.context(self.open_page)

		self.assertIn(reach.UNCOUNTED, context)
		self.assertNotIn("on 3 pages", context)

	def test_a_run_that_can_search_the_site_hears_none_of_it(self):
		with patch.object(reach, "MAX_PAGES", 10_000):
			context = self.context(self.open_page, page_tools, search_tools)

		self.assertIn("This site's host leaves you without these tools", context)
		self.assertNotIn("Besides this page", context)
		self.assertNotIn("Where the components", context)
