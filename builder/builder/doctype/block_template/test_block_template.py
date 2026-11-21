# Copyright (c) 2024, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import json
import re

import frappe
from bs4 import BeautifulSoup
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_page.builder_page import get_block_html


class TestBlockTemplate(FrappeTestCase):
	def test_overlay_opens_on_target_and_closes_to_a_hash_that_targets_nothing(self):
		html, css, _, _ = get_block_html([get_shipped_template_block("overlay")])
		soup = BeautifulSoup(html, "html.parser")
		overlay = soup.find(id=True)
		style_class = overlay["class"][0]

		base_rule = re.search(rf"\.{style_class} \{{([^}}]*)\}}", css).group(1)
		self.assertIn("visibility: hidden;", base_rule)
		self.assertIn("opacity: 0;", base_rule)
		self.assertIn(f".{style_class}:target {{ visibility: visible; }}", css)
		self.assertIn(f".{style_class}:target {{ opacity: 1; }}", css)

		opener = soup.find("a", href=f"#{overlay['id']}")
		self.assertIsNotNone(opener)
		self.assertNotIn(overlay, opener.parents)

		# "#" and "#top" scroll to the top of the page, and a hash naming an id scrolls to it
		scrolling_hashes = {"#top", *(f"#{tag['id']}" for tag in soup.find_all(id=True))}
		for link in overlay.find_all("a"):
			self.assertRegex(link["href"], r"^#.")
			self.assertNotIn(link["href"], scrolling_hashes)


def get_shipped_template_block(folder):
	path = frappe.get_module_path("builder", "builder_block_template", folder, f"{folder}.json")
	with open(path) as f:
		return json.loads(json.load(f)["block"])
