# Copyright (c) 2023, asdf and Contributors
# See license.txt

import json

import frappe
from frappe.desk.form.load import getdoc
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response_content

from builder.utils import Block

repeater_page_data_script = """
data.update({
	"items": [
		{"name": "Item 1", "price": "$10"},
		{"name": "Item 2", "price": "$20"}
	]
})
"""

page_data_script = """
data.update({
	"name": "John Doe",
	"color": "red",
	"padding": "20px",
	"link": "https://example.com",
})
"""

custom_data_script = 'data.update({"name_new": "Jane Doe",})'

block_data_script = """
block.update({
	"content": "Custom Block Data",
	"items": [
		{"name": "Item 1", "price": "$10"},
		{"name": "Item 2", "price": "$20"}
	]
})
"""


class TestBuilderPage(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		cls.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"name": "test-page",
				"page_title": "Test Page",
				"published": 1,
				"route": "/test-page",
				"blocks": json.dumps(
					[
						Block(
							element="body",
							baseStyles={"background": "red", "fontFamily": "Inter"},
							customAttributes={"dir": "ltr"},
							children=[
								Block(
									element="h1",
									innerHTML="Hello World!",
									baseStyles={
										"color": "blue",
										"fontFamily": "Comic Sans MS",
										"fontWeight": "500",
									},
								)
							],
						).as_dict()
					]
				),
			}
		).insert(ignore_if_duplicate=True)
		cls.page_with_dynamic_route = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Test Page Dynamic Route",
				"published": 1,
				"route": "/test-page-dynamic-route/<name>",
				"dynamic_route": 1,
				"blocks": json.dumps(
					[
						Block(
							element="body", children=[Block(element="h1", innerHTML="Dynamic Content!")]
						).as_dict()
					]
				),
			}
		).insert(ignore_if_duplicate=True)

	def test_can_render(self):
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)

	def test_onload(self):
		getdoc("Builder Page", self.page.name)
		self.assertEqual(frappe.response.docs[0].get("__onload").get("builder_path"), "builder")

	def test_dynamic_route(self):
		from frappe.utils import get_html_for_route

		content = get_html_for_route("/test-page-dynamic-route/123")
		self.assertTrue("Dynamic Content!" in content)

	def test_publish_unpublish(self):
		self.page.unpublish()
		from frappe.utils import get_html_for_route

		content = get_html_for_route("/test-page")
		self.assertTrue("window.is_404 = true;" in content)

		self.page.publish()
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)

	def test_dynamic_values(self):
		body = Block(element="body")
		header = Block(element="h1", innerHTML="Hello")
		sub_header = Block(element="h2", innerHTML="Content")
		link = Block(element="a", innerHTML="Link")

		header.attach_dynamic_values({"key": "name", "type": "key", "property": "innerHTML"})
		sub_header.attach_dynamic_values(
			{"key": "color", "type": "style", "property": "color"},
			{"key": "padding", "type": "style", "property": "padding"},
		)
		link.attach_dynamic_values({"key": "link", "type": "attribute", "property": "href"})

		body.attach_children(header, sub_header, link)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Dynamic Values Test",
				"published": 1,
				"route": "/dynamic-values-test",
				"page_data_script": page_data_script,
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/dynamic-values-test")
			self.assertTrue("John Doe" in get_html_for(content, "tag", "h1"))
			self.assertTrue("color: red;padding: 20px;" in get_html_for(content, "tag", "h2"))
			self.assertTrue('href="https://example.com"' in get_html_for(content, "tag", "a"))
		finally:
			page.delete()

	def test_repeater_block_dynamic_values(self):
		body = Block(element="body")
		repeater_block = Block(element="div", isRepeaterBlock=True)
		wrapper_div = Block(element="div")
		item_name = Block(element="h2")
		item_price = Block(element="span")

		repeater_block.attach_data_key("items", "dataKey")
		item_name.attach_dynamic_values({"key": "name", "type": "key", "property": "innerHTML"})
		item_price.attach_dynamic_values({"key": "price", "type": "key", "property": "innerHTML"})

		wrapper_div.attach_children(item_name, item_price)
		repeater_block.attach_children(wrapper_div)
		body.attach_children(repeater_block)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Repeater Block Test",
				"published": 1,
				"route": "/repeater-block-test",
				"page_data_script": repeater_page_data_script,
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/repeater-block-test")
			self.assertTrue("Item 1" in get_html_for(content, "tag", "h2"))
			self.assertTrue("$10" in get_html_for(content, "tag", "span"))
			self.assertTrue("Item 2" in get_html_for(content, "tag", "h2", index=1))
			self.assertTrue("$20" in get_html_for(content, "tag", "span", index=1))

		finally:
			page.delete()

	def test_component_dynamic_values(self):
		comp_root = Block(element="div", blockId="comp-block-1")
		comp_name = Block(element="h1", blockId="comp-block-1-1", innerHTML="Hello")

		comp_name.attach_dynamic_values({"key": "name", "type": "key", "property": "innerHTML"})
		comp_root.attach_children(comp_name)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": comp_root.as_json(),
			}
		).insert()

		body = Block(element="body")
		comp_root_copy = Block(extendedFromComponent=component.name)
		comp_name_copy = Block(isChildOfComponent=component.name, referenceBlockId="comp-block-1-1")

		comp_root_copy.attach_children(comp_name_copy)
		body.attach_children(comp_root_copy)

		page_with_component_no_overrides = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Dynamic Values Test",
				"published": 1,
				"route": "/component-dynamic-values-test-no-overrides",
				"page_data_script": page_data_script,
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		comp_name_copy.attach_dynamic_values({"key": "name_new", "type": "key", "property": "innerHTML"})

		page_with_component_having_overrides = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Dynamic Values Test",
				"published": 1,
				"route": "/component-dynamic-values-test-with-overrides",
				"page_data_script": custom_data_script,
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		comp_name_copy.clear_dynamic_values()
		comp_name_copy.attach_dynamic_values(
			{"key": "non_existent_key", "type": "key", "property": "innerHTML"}
		)

		page_with_component_having_bad_overrides = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Dynamic Values Test",
				"published": 1,
				"route": "/component-dynamic-values-test-with-bad-overrides",
				"page_data_script": custom_data_script,
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content_with_no_overrides = get_response_content("/component-dynamic-values-test-no-overrides")
			content_with_overrides = get_response_content("/component-dynamic-values-test-with-overrides")
			content_with_bad_overrides = get_response_content(
				"/component-dynamic-values-test-with-bad-overrides"
			)
			self.assertEqual(
				"John Doe", get_html_for(content_with_no_overrides, "tag", "h1", only_content=True)
			)
			self.assertEqual("Jane Doe", get_html_for(content_with_overrides, "tag", "h1", only_content=True))
			self.assertEqual(
				"Hello", get_html_for(content_with_bad_overrides, "tag", "h1", only_content=True)
			)
		finally:
			page_with_component_no_overrides.delete()
			page_with_component_having_overrides.delete()
			page_with_component_having_bad_overrides.delete()
			component.delete()

	def test_block_data(self):
		body = Block(element="body")
		wrapper = Block(element="div", blockDataScript=block_data_script)
		content_dynamic = Block(element="h4", innerHTML="Block Content")
		content_fallback = Block(element="h4", innerHTML="Block Content")

		content_dynamic.attach_dynamic_values(
			{"key": "content", "type": "key", "property": "innerHTML", "comesFrom": "blockDataScript"},
		)
		content_fallback.attach_dynamic_values(
			{"key": "no_key", "type": "key", "property": "innerHTML", "comesFrom": "blockDataScript"},
		)

		wrapper.attach_children(content_dynamic, content_fallback)
		body.attach_children(wrapper)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Block Data Test",
				"published": 1,
				"route": "/block-data-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/block-data-test")
			self.assertEqual("Custom Block Data", get_html_for(content, "tag", "h4", only_content=True))
			self.assertEqual("Block Content", get_html_for(content, "tag", "h4", index=1, only_content=True))
		finally:
			page.delete()

	def test_block_props(self):
		body = Block(element="body")
		div_wrapper = Block(
			element="div",
			props={
				"first_name": {
					"isDynamic": False,
					"isPassedDown": True,
					"value": "John",
					"isStandard": False,
				},
				"last_name": {
					"isDynamic": False,
					"isPassedDown": False,
					"value": "Doe",
					"isStandard": False,
				},
			},
			blockDataScript=block_data_script,
		)
		content_static_prop = Block(element="h4", innerHTML="Block Props Content")
		content_dynamic_prop = Block(
			element="h4",
			innerHTML="Block Props Content",
			props={
				"content": {
					"isDynamic": True,
					"comesFrom": "blockDataScript",
					"isPassedDown": True,
					"value": "content",
					"isStandard": False,
				},
			},
		)
		content_fallback = Block(element="h4", innerHTML="Block Props Content")

		content_static_prop.attach_dynamic_values(
			{"key": "first_name", "type": "key", "property": "innerHTML", "comesFrom": "props"},
		)
		content_dynamic_prop.attach_dynamic_values(
			{"key": "content", "type": "key", "property": "innerHTML", "comesFrom": "props"},
		)
		content_fallback.attach_dynamic_values(
			{"key": "last_name", "type": "key", "property": "innerHTML", "comesFrom": "props"},
		)

		div_wrapper.attach_children(content_static_prop, content_dynamic_prop, content_fallback)
		body.attach_children(div_wrapper)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Block Props Test",
				"published": 1,
				"route": "/block-props-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/block-props-test")
			self.assertEqual("John", get_html_for(content, "tag", "h4", only_content=True))
			self.assertEqual(
				"Custom Block Data", get_html_for(content, "tag", "h4", index=1, only_content=True)
			)
			self.assertEqual(
				"Block Props Content", get_html_for(content, "tag", "h4", index=2, only_content=True)
			)
		finally:
			page.delete()

	@classmethod
	def tearDownClass(cls):
		cls.page.delete()
		cls.page_with_dynamic_route.delete()


def get_html_for(html, type, value, index=None, only_content=False):
	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, "html.parser")
	if type == "tag":
		results = soup.find_all(value)
		result = (
			results[index] if index is not None and index < len(results) else results[0] if results else None
		)
		if only_content and result:
			return result.decode_contents()
		return str(result) if result else ""
	if type == "attribute":
		results = soup.find_all(attrs=value)
		result = (
			results[index] if index is not None and index < len(results) else results[0] if results else None
		)
		return str(result) if result else ""
