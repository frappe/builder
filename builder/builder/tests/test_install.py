import frappe
from frappe.tests.utils import FrappeTestCase

from builder.install import (
	WEBSITE_SIDEBAR_ITEM,
	add_builder_to_website_sidebar,
	has_sidebar_layers,
	remove_builder_from_website_sidebar,
)


class TestWebsiteSidebar(FrappeTestCase):
	def setUp(self):
		if not has_sidebar_layers():
			self.skipTest("Sidebar layers need Frappe v17")

	def test_builder_is_added_to_the_website_sidebar_once(self):
		remove_builder_from_website_sidebar()
		self.assertNotIn(WEBSITE_SIDEBAR_ITEM["url"], self.website_sidebar_urls())

		add_builder_to_website_sidebar()
		add_builder_to_website_sidebar()
		self.assertEqual(self.website_sidebar_urls().count(WEBSITE_SIDEBAR_ITEM["url"]), 1)

	def test_uninstall_removes_builder_from_the_website_sidebar(self):
		add_builder_to_website_sidebar()
		remove_builder_from_website_sidebar()
		self.assertNotIn(WEBSITE_SIDEBAR_ITEM["url"], self.website_sidebar_urls())

	def website_sidebar_urls(self) -> list[str]:
		from frappe.desk.doctype.sidebar.sidebar import resolve_sidebar

		sidebar = resolve_sidebar("Website", "Administrator")
		return [item.get("url") for item in sidebar.items]
