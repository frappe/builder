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

	def test_image_hotspots_are_plain_links_that_open_without_script(self):
		html, css, _, _ = get_block_html([get_shipped_template_block("image_hotspots")])
		hotspots = re.findall(r'<a class="(fb-\w+)[^"]*" href="([^"]+)"', html)

		self.assertEqual(len(hotspots), 3)
		for style_class, href in hotspots:
			# a hash that names no element, so following the placeholder does not scroll
			self.assertRegex(href, r"^#[\w-]+$")
			self.assertNotIn(f'id="{href[1:]}"', html)

			# placed in % and centred on its spot, so it stays there at every width
			rule = re.search(rf"\.{style_class} {{([^}}]*)}}", css).group(1)
			self.assertRegex(rule, r"left: [\d.]+%;")
			self.assertRegex(rule, r"top: [\d.]+%;")
			self.assertIn("transform: translate(-50%, -50%)", rule)

			# hover and keyboard focus open the label, and it stays open below desktop width
			open_width = re.search(rf"\.{style_class}:hover {{ max-width: (\w+); }}", css).group(1)
			self.assertIn(f".{style_class}:focus-visible {{ max-width: {open_width}; }}", css)
			self.assertIn(f".{style_class}:focus-visible {{ outline: ", css)
			self.assertIn(
				f"@media only screen and (max-width: 1023px) {{ .{style_class} {{ max-width: {open_width}; }} }}",
				css,
			)

		# the image keeps its box while it loads, so the hotspots are not clipped to nothing
		image = BeautifulSoup(html, "html.parser").find("img")
		self.assertEqual((image["width"], image["height"]), ("1920", "1280"))

		# the page's client script tag stays empty
		self.assertNotRegex(html, r"<script>(?!</script>)")


def get_shipped_template_block(folder):
	path = frappe.get_module_path("builder", "builder_block_template", folder, f"{folder}.json")
	with open(path) as f:
		return json.loads(json.load(f)["block"])
