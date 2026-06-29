# Copyright (c) 2023, asdf and Contributors
# See license.txt


import frappe
from frappe.desk.form.load import getdoc
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response, get_response_content

from builder.utils import Block

repeater_page_data_script = """
data.update({
	"items": [
		{"name": "Item 1", "price": "$10"},
		{"name": "Item 2", "price": "$20"}
	],
	"item_group": [
		{
			"group": [
				{"name": "Item A1", "price": "$10"},
				{"name": "Item A2", "price": "$20"}
			],
		},
		{
			"group": [
				{"name": "Item B1", "price": "$15"},
				{"name": "Item B2", "price": "$25"}
			],
		}
	]
})
"""

page_data_script = """
data.update({
	"name": "John Doe",
	"color": "red",
	"padding": "20px",
	"link": "https://example.com",
	"role": "admin",
})
"""

component_data_script = """
component.update({
	"name": "John Doe",
	"name_new": "Jane Doe",
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
				"blocks": Block(
					element="div",
					originalElement="body",
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
				).as_json(wrap_in_array=True),
			}
		).insert(ignore_if_duplicate=True)
		cls.page_with_dynamic_route = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Test Page Dynamic Route",
				"published": 1,
				"route": "/test-page-dynamic-route/<name>",
				"dynamic_route": 1,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[Block(element="h1", innerHTML="Dynamic Content!")],
				).as_json(wrap_in_array=True),
			}
		).insert(ignore_if_duplicate=True)

	def test_can_render(self):
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)

	def test_get_preview_html_preserves_outer_request(self):
		"""get_preview_html() fakes a request via set_request(); when it runs
		synchronously inside a real web request (e.g. run_doc_method) it must not
		clobber it — doing so dropped the request's after_response and broke
		sync_database with a 500."""
		from frappe.utils import CallbackManager
		from werkzeug.test import EnvironBuilder
		from werkzeug.wrappers import Request

		previous = getattr(frappe.local, "request", None)
		try:
			req = Request(EnvironBuilder(path="/api/method/run_doc_method").get_environ())
			sentinel = CallbackManager()
			req.after_response = sentinel
			frappe.local.request = req

			self.page.get_preview_html()

			self.assertIs(frappe.local.request, req)
			self.assertIs(frappe.local.request.after_response, sentinel)
		finally:
			frappe.local.request = previous

	def test_onload(self):
		getdoc("Builder Page", self.page.name)
		self.assertEqual(frappe.response.docs[0].get("__onload").get("builder_path"), "builder")

	def test_dynamic_route(self):
		from frappe.utils import get_html_for_route

		content = get_html_for_route("/test-page-dynamic-route/123")
		self.assertTrue("Dynamic Content!" in content)

	def test_publish_unpublish(self):
		self.page.unpublish()
		# An unpublished route is "not found". The rendered body varies (a site may
		# define a custom Builder 404 page via www/404.py), so assert the 404 status
		# and that the page's own content is no longer served.
		response = get_response("/test-page")
		self.assertEqual(response.status_code, 404)
		self.assertNotIn("Hello World!", frappe.safe_decode(response.get_data()))

		self.page.publish()
		content = get_response_content("/test-page")
		self.assertTrue("Hello World!" in content)

	def test_client_script(self):
		client_script_js = frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"script_type": "JavaScript",
				"script": 'console.log("Test");',
			}
		).insert()

		client_script_css = frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"script_type": "CSS",
				"script": "body { background-color: red; }",
			}
		).insert()

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Client Script Test",
				"published": 1,
				"route": "/client-script-test",
				"blocks": Block(
					element="div",
					originalElement="body",
				).as_json(wrap_in_array=True),
			}
		).insert()

		client_script_js_row = frappe.get_doc(
			{
				"doctype": "Builder Page Client Script",
				"parent": page.name,
				"builder_script": client_script_js.name,
				"parenttype": "Builder Page",
				"parentfield": "client_scripts",
			}
		).insert()

		client_script_css_row = frappe.get_doc(
			{
				"doctype": "Builder Page Client Script",
				"parent": page.name,
				"builder_script": client_script_css.name,
				"parenttype": "Builder Page",
				"parentfield": "client_scripts",
			}
		).insert()

		try:
			content = get_response_content("/client-script-test")
			self.assertTrue(
				client_script_js.public_url in get_html_for(content, "attribute", "src", list_all=True)
			)
			self.assertTrue(
				client_script_css.public_url in get_html_for(content, "attribute", "href", list_all=True)
			)
		finally:
			client_script_js_row.delete()
			client_script_css_row.delete()
			page.delete()
			client_script_js.delete()
			client_script_css.delete()

	def test_dynamic_values(self):
		body = Block(
			element="div",
			originalElement="body",
		)
		header = Block(element="h1", innerHTML="Hello")
		sub_header = Block(element="h2", innerHTML="Content")
		link = Block(element="a", innerHTML="Link")

		header.set_dynamic_value("name", "key", "innerHTML")

		sub_header.set_dynamic_value("color", "style", "color")
		sub_header.set_dynamic_value("padding", "style", "padding")

		link.set_dynamic_value("link", "attribute", "href")
		custom_attr_block = Block(element="div", customAttributes={"data-role": "guest"})
		custom_attr_block.set_dynamic_value("role", "attribute", "data-role")
		body.attach_children(header, sub_header, link, custom_attr_block)

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
			self.assertEqual("admin", get_html_for(content, "attribute", "data-role"))
		finally:
			page.delete()

	def test_repeater_block_dynamic_values(self):
		body = Block(
			element="div",
			originalElement="body",
		)
		repeater_block = Block(element="div", isRepeaterBlock=True)
		wrapper_div = Block(element="div")
		item_name = Block(element="h2")
		item_price = Block(element="span")

		repeater_block.attach_data_key("items", "dataKey")
		item_name.set_dynamic_value("name", "key", "innerHTML")
		item_price.set_dynamic_value("price", "key", "innerHTML")

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
		"Test dynamic values in component with and without overrides"
		component_root = Block(element="div", blockId="comp-block-1")
		component_header = Block(element="h1", blockId="comp-block-1-1", innerHTML="Fallback Content")

		component_header.set_dynamic_value("name", "key", "innerHTML", "componentData")
		component_root.attach_children(component_header)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": component_root.as_json(),
				"component_data_script": component_data_script,
			}
		).insert()

		body = Block(
			element="div",
			originalElement="body",
		)
		component_root_copy = Block(extendedFromComponent=component.name)
		component_header_copy = Block(isChildOfComponent=component.name, referenceBlockId="comp-block-1-1")

		component_root_copy.attach_children(component_header_copy)
		body.attach_children(component_root_copy)

		# Using a component with dynamic values without any overrides
		page_with_component_no_overrides = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Dynamic Values Test",
				"published": 1,
				"route": "/component-dynamic-values-test-no-overrides",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		# Using a component with dynamic values with valid overrides to the dynamic values
		component_header_copy.set_dynamic_value("name_new", "key", "innerHTML", "componentData")

		page_with_component_having_overrides = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Dynamic Values Test",
				"published": 1,
				"route": "/component-dynamic-values-test-with-overrides",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		# Using a component with dynamic values with invalid overrides to the dynamic values
		component_header_copy.clear_dynamic_values()
		component_header_copy.set_dynamic_value("non_existent_key", "key", "innerHTML", "componentData")

		page_with_component_having_bad_overrides = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Dynamic Values Test",
				"published": 1,
				"route": "/component-dynamic-values-test-with-bad-overrides",
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
				"Fallback Content", get_html_for(content_with_bad_overrides, "tag", "h1", only_content=True)
			)
		finally:
			page_with_component_no_overrides.delete()
			page_with_component_having_overrides.delete()
			page_with_component_having_bad_overrides.delete()
			component.delete()

	def test_visibility_condition_from_page_data(self):
		body = Block(
			element="div",
			originalElement="body",
		)
		header = Block(element="h1", innerHTML="Visible Header H1")
		hidden_header = Block(element="h2", innerHTML="Hidden Header H2")
		hidden_header_h3 = Block(element="h3", innerHTML="Hidden Header H3")
		header_h4 = Block(element="h4", innerHTML="Header H4")
		header_h5 = Block(element="h5", innerHTML="Header H5")

		header.visibilityCondition = {"key": "is_header_visible", "comesFrom": "dataScript"}
		hidden_header.visibilityCondition = {"key": "is_hidden_header_visible", "comesFrom": "dataScript"}
		hidden_header_h3.visibilityCondition = "is_hidden_header_visible"  # legacy
		header_h4.visibilityCondition = ""
		header_h5.visibilityCondition = {"key": "", "comesFrom": "dataScript"}

		body.attach_children(header, hidden_header, hidden_header_h3, header_h4, header_h5)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Visibility Key Test",
				"published": 1,
				"route": "/visibility-key-test",
				"page_data_script": 'data.update({"is_header_visible": True,"is_hidden_header_visible": False})',
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()
		try:
			content = get_response_content("/visibility-key-test")
			self.assertTrue("Visible Header H1" in get_html_for(content, "tag", "h1"))
			self.assertFalse("Hidden Header H2" in get_html_for(content, "tag", "h2"))
			self.assertFalse("Hidden Header H3" in get_html_for(content, "tag", "h3"))
			self.assertTrue("Header H4" in get_html_for(content, "tag", "h4"))
			self.assertTrue("Header H5" in get_html_for(content, "tag", "h5"))
		finally:
			page.delete()

	def test_redirect_from_page_data_script(self):
		body = Block(element="div", originalElement="body")
		body.attach_children(Block(element="h1", innerHTML="Should not render"))

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Redirect Test",
				"published": 1,
				"route": "/redirect-test",
				"page_data_script": 'redirect("/login", 302)',
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()
		try:
			response = get_response("/redirect-test")
			self.assertEqual(response.status_code, 302)
			self.assertEqual(response.headers.get("Location"), "/login")

			self.assertEqual(page.get_page_data(), {})
		finally:
			frappe.local.flags.redirect_location = None
			page.delete()

	def test_component_client_script(self):
		component_root = Block(element="div", blockId="comp-root")
		component_content = Block(element="h4", blockId="comp-content", innerHTML="Component Content")
		component_root.attach_children(component_content)
		component_js = 'this.innerHTML = "</script><p>Component Script</p>";'
		component_css = 'h4::after { content: "</style><p>Component Style</p>"; }'
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": component_root.as_json(),
				"component_js": component_js,
				"component_css": component_css,
			}
		).insert()

		body = Block(
			element="div",
			originalElement="body",
		)
		component_root_copy = Block(extendedFromComponent=component.name)
		component_content_copy = Block(
			isChildOfComponent=component.name,
			referenceBlockId="comp-content",
		)
		component_root_copy.attach_children(component_content_copy)
		body.attach_children(component_root_copy)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Client Script Test",
				"published": 1,
				"route": "/component-client-script-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/component-client-script-test")
			self.assertNotIn(component_js, content)
			self.assertNotIn(component_css, content)
			self.assertIn(r"<\/script><p>Component Script</p>", content)
			self.assertIn(r"<\/style><p>Component Style</p>", content)
		finally:
			page.delete()
			component.delete()

	def test_component_client_script_receives_context(self):
		component_data_for_script = """
component.update({
	"component_data": {"greeting": "hello from component data"},
})
"""
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": Block(element="div", blockId="script-root").as_json(),
				"component_data_script": component_data_for_script,
				"component_props": {
					"title": {
						"label": "Title",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": "Default Title",
						"propOptions": {
							"isRequired": False,
							"type": "string",
							"options": {"defaultValue": "Default Title"},
						},
					},
				},
				"component_js": 'this.dataset.received = "ok";',
			}
		).insert()

		body = Block(element="div", originalElement="body")
		component_root_copy = Block(
			extendedFromComponent=component.name,
			props={
				"title": {
					"label": "Title",
					"isStandard": True,
					"isDynamic": False,
					"isPassedDown": True,
					"comesFrom": None,
					"value": "Overridden Title",
					"propOptions": {
						"isRequired": False,
						"type": "string",
						"options": {"defaultValue": "Default Title"},
					},
				},
			},
		)
		body.attach_children(component_root_copy)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Client Script Args Test",
				"published": 1,
				"route": "/component-client-script-args-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/component-client-script-args-test")
			self.assertIn("component_data, props", content)
			self.assertIn('"greeting": "hello from component data"', content)
			self.assertIn('"title": "Overridden Title"', content)
			self.assertNotIn("/assets/builder/js/reactivity.js", content)
			self.assertRegex(
				content,
				r"client_script_[a-z0-9_]+\)\.call\("
				r"document\.querySelector\('\[data-block-uid=\"[^\"]+\"\]'\), "
				r'\{[^}]*"greeting": "hello from component data"[^}]*\}, '
				r'\{[^}]*"title": "Overridden Title"[^}]*\}\)',
			)
		finally:
			page.delete()
			component.delete()

	def test_component_props(self):
		component_root = Block(element="div", blockId="wrapper-block")
		content_static_prop = Block(
			blockId="static-content", element="h4", innerHTML="Component Props Content"
		)
		content_dynamic_prop = Block(
			blockId="dynamic-content", element="h4", innerHTML="Component Props Content"
		)
		content_last_name = Block(
			blockId="last-name-content", element="h4", innerHTML="Component Props Content"
		)
		content_fallback = Block(
			blockId="fallback-content", element="h4", innerHTML="Component Props Content"
		)

		content_static_prop.set_dynamic_value("first_name", "key", "innerHTML", "props")
		content_dynamic_prop.set_dynamic_value("name", "key", "innerHTML", "componentData")
		content_last_name.set_dynamic_value("last_name", "key", "innerHTML", "props")
		content_fallback.set_dynamic_value("middle_name", "key", "innerHTML", "props")

		component_root.attach_children(
			content_static_prop, content_dynamic_prop, content_last_name, content_fallback
		)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": component_root.as_json(),
				"component_props": {
					"first_name": {
						"label": "First Name",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": "John",
						"propOptions": {
							"isRequired": False,
							"type": "string",
							"options": {"defaultValue": ""},
						},
					},
					"last_name": {
						"label": "Last Name",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": "Doe",
						"propOptions": {
							"isRequired": False,
							"type": "string",
							"options": {"defaultValue": ""},
						},
					},
				},
				"component_data_script": component_data_script,
			}
		).insert()

		body = Block(
			element="div",
			originalElement="body",
		)
		component_root_copy = Block(extendedFromComponent=component.name)
		content_static_copy = Block(isChildOfComponent=component.name, referenceBlockId="static-content")
		content_dynamic_copy = Block(isChildOfComponent=component.name, referenceBlockId="dynamic-content")
		content_last_name_copy = Block(
			isChildOfComponent=component.name, referenceBlockId="last-name-content"
		)
		content_fallback_copy = Block(isChildOfComponent=component.name, referenceBlockId="fallback-content")
		component_root_copy.attach_children(
			content_static_copy,
			content_dynamic_copy,
			content_last_name_copy,
			content_fallback_copy,
		)
		body.attach_children(component_root_copy)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Props Test",
				"published": 1,
				"route": "/component-props-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/component-props-test")
			self.assertEqual("John", get_html_for(content, "tag", "h4", only_content=True))
			self.assertEqual("John Doe", get_html_for(content, "tag", "h4", index=1, only_content=True))
			self.assertEqual("Doe", get_html_for(content, "tag", "h4", index=2, only_content=True))
			self.assertEqual(
				"Component Props Content", get_html_for(content, "tag", "h4", index=3, only_content=True)
			)
		finally:
			page.delete()
			component.delete()

	def test_std_props(self):
		component_root = Block(
			blockId="header-block",
			element="header",
			blockName="header",
		)

		component_title_block = Block(blockId="title-block", element="h1", innerHTML="Header Title")
		component_title_block.set_dynamic_value("title", "key", "innerHTML", "props")

		component_age_block = Block(blockId="age-block", element="h4", innerHTML="Age")
		component_age_block.set_dynamic_value("age", "key", "innerHTML", "props")

		component_badge_block = Block(blockId="badge-block", element="h6", innerHTML="Badge")
		component_badge_block.visibilityCondition = {
			"key": "show_badge",
			"comesFrom": "props",
		}

		component_root.attach_children(component_title_block, component_age_block, component_badge_block)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": component_root.as_json(),
				"component_props": {
					"title": {
						"label": "Title",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": None,
						"propOptions": {
							"isRequired": False,
							"type": "string",
							"options": {"defaultValue": "Default Header Title"},
						},
					},
					"age": {
						"label": "Age",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": None,
						"propOptions": {
							"isRequired": False,
							"type": "number",
							"options": {"defaultValue": 25},
						},
					},
					"show_badge": {
						"label": "Show Badge",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": None,
						"propOptions": {
							"isRequired": False,
							"type": "boolean",
							"options": {"defaultValue": False},
						},
					},
				},
			}
		).insert()

		body = Block(
			element="div",
			originalElement="body",
		)

		component_root_copy = Block(extendedFromComponent=component.name)
		component_title_block_copy = Block(isChildOfComponent=component.name, referenceBlockId="title-block")
		component_age_block_copy = Block(isChildOfComponent=component.name, referenceBlockId="age-block")
		component_badge_block_copy = Block(isChildOfComponent=component.name, referenceBlockId="badge-block")

		component_root_copy.attach_children(
			component_title_block_copy, component_age_block_copy, component_badge_block_copy
		)
		body.attach_children(component_root_copy)

		page_with_default_values = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Std Props Test",
				"published": 1,
				"route": "/block-std-props-test-no-overrides",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		component_root_copy.props = {
			"title": {
				"label": "Title",
				"isStandard": True,
				"isDynamic": False,
				"isPassedDown": True,
				"comesFrom": None,
				"value": "Overridden Header Title",
				"propOptions": {
					"isRequired": False,
					"type": "string",
					"options": {"defaultValue": "Default Header Title"},
				},
			},
			"age": {
				"label": "Age",
				"isStandard": True,
				"isDynamic": False,
				"isPassedDown": True,
				"comesFrom": None,
				"value": 29,
				"propOptions": {
					"isRequired": False,
					"type": "number",
					"options": {"defaultValue": 25},
				},
			},
			"show_badge": {
				"label": "Show Badge",
				"isStandard": True,
				"isDynamic": False,
				"isPassedDown": True,
				"comesFrom": None,
				"value": True,
				"propOptions": {
					"isRequired": False,
					"type": "boolean",
					"options": {"defaultValue": False},
				},
			},
		}

		page_with_overridden_values = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Std Props Test With Overrides",
				"published": 1,
				"route": "/block-std-props-test-overrides",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content_with_default_values = get_response_content("/block-std-props-test-no-overrides")
			content_with_overridden_values = get_response_content("/block-std-props-test-overrides")

			self.assertEqual(
				"Default Header Title",
				get_html_for(content_with_default_values, "tag", "h1", only_content=True),
			)
			self.assertEqual(
				"25.0", get_html_for(content_with_default_values, "tag", "h4", only_content=True)
			)
			self.assertFalse("Badge" in get_html_for(content_with_default_values, "tag", "h6"))

			self.assertEqual(
				"Overridden Header Title",
				get_html_for(content_with_overridden_values, "tag", "h1", only_content=True),
			)
			self.assertEqual(
				"29.0", get_html_for(content_with_overridden_values, "tag", "h4", only_content=True)
			)
			self.assertTrue("Badge" in get_html_for(content_with_overridden_values, "tag", "h6"))
		finally:
			page_with_default_values.delete()
			page_with_overridden_values.delete()
			component.delete()

	def test_repeater_from_std_props(self):
		component_root = Block(
			blockId="navbar-wrapper-block",
			element="header",
			blockName="navbar",
		)
		component_repeater_block = Block(
			blockId="repeater-block",
			element="nav",
			blockName="nav",
			isRepeaterBlock=True,
		)
		component_repeater_block.attach_data_key("links", "innerHTML", type="key", comesFrom="props")
		component_link_block = Block(
			blockId="link-block", element="a", innerHTML="Home", attributes={"href": "/home"}
		)
		component_link_block.set_dynamic_value("key", "key", "innerHTML")
		component_link_block.set_dynamic_value("value", "attribute", "href")

		component_repeater_block.attach_children(component_link_block)
		component_root.attach_children(component_repeater_block)

		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"block": component_root.as_json(),
				"component_props": {
					"links": {
						"label": "Links",
						"isStandard": True,
						"isDynamic": False,
						"isPassedDown": True,
						"comesFrom": None,
						"value": None,
						"propOptions": {
							"isRequired": False,
							"type": "object",
							"options": {
								"minItems": None,
								"maxItems": None,
								"defaultValue": {
									"1. Home": "/",
									"2. Products": "/products",
									"3. About Us": "/about",
								},
							},
						},
					}
				},
			}
		).insert()

		body = Block(
			element="div",
			originalElement="body",
		)
		component_root_copy = Block(extendedFromComponent=component.name)
		component_repeater_block_copy = Block(
			isChildOfComponent=component.name, referenceBlockId="repeater-block", isRepeaterBlock=True
		)
		component_link_block_copy = Block(isChildOfComponent=component.name, referenceBlockId="link-block")
		component_repeater_block_copy.attach_children(component_link_block_copy)
		component_root_copy.attach_children(component_repeater_block_copy)
		body.attach_children(component_root_copy)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Std Props Repeater Test",
				"published": 1,
				"route": "/block-std-props-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()
		try:
			content = get_response_content("/block-std-props-test")
			self.assertEqual("1. Home", get_html_for(content, "tag", "a", only_content=True))
			self.assertTrue('href="/"' in get_html_for(content, "tag", "a", only_content=False))
			self.assertEqual("2. Products", get_html_for(content, "tag", "a", index=1, only_content=True))
			self.assertTrue(
				'href="/products"' in get_html_for(content, "tag", "a", index=1, only_content=False)
			)
			self.assertEqual("3. About Us", get_html_for(content, "tag", "a", index=2, only_content=True))
			self.assertTrue('href="/about"' in get_html_for(content, "tag", "a", index=2, only_content=False))
		finally:
			page.delete()
			component.delete()

	def test_dark_mode_img(self):
		body = Block(
			element="div",
			originalElement="body",
		)
		image_block = Block(
			element="img",
			attributes={
				"src": "/files/light-mode-image.png",
				"darkSrc": "/files/dark-mode-image.png",
				"alt": "Test Image",
			},
		)
		image_block_only_dark_mode = Block(
			element="img",
			attributes={
				"darkSrc": "/files/another-dark-mode-image.png",
				"alt": "Test Image",
			},
		)
		body.attach_children(image_block, image_block_only_dark_mode)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Dark Mode Image Test",
				"published": 1,
				"route": "/dark-mode-image-test",
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/dark-mode-image-test")
			self.assertTrue(
				'src="/files/light-mode-image.png"' in get_html_for(content, "tag", "img", only_content=False)
			)
			self.assertTrue(
				'srcset="/files/dark-mode-image.png"'
				in get_html_for(content, "tag", "source", only_content=False)
			)
			self.assertTrue(
				'src="/files/another-dark-mode-image.png"'
				in get_html_for(content, "tag", "img", index=1, only_content=False)
			)
		finally:
			page.delete()

	def test_nested_repeater_from_page_data(self):
		body = Block(
			element="div",
			originalElement="body",
		)
		parent_repeater = Block(element="div", isRepeaterBlock=True)
		child_repeater = Block(element="div", isRepeaterBlock=True)
		wrapper_div = Block(element="div")

		parent_repeater.attach_data_key("item_group", "dataKey")
		child_repeater.attach_data_key("group", "dataKey")

		item_name = Block(element="h2")
		item_price = Block(element="span")

		item_name.set_dynamic_value("name", "key", "innerHTML")
		item_price.set_dynamic_value("price", "key", "innerHTML")

		wrapper_div.attach_children(item_name, item_price)
		child_repeater.attach_children(wrapper_div)
		parent_repeater.attach_children(child_repeater)
		body.attach_children(parent_repeater)

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Nested Repeater Blocks Test",
				"published": 1,
				"route": "/nested-repeater-blocks-test",
				"page_data_script": repeater_page_data_script,
				"blocks": body.as_json(wrap_in_array=True),
			}
		).insert()

		try:
			content = get_response_content("/nested-repeater-blocks-test")
			self.assertTrue("Item A1" in get_html_for(content, "tag", "h2"))
			self.assertTrue("$10" in get_html_for(content, "tag", "span"))
			self.assertTrue("Item A2" in get_html_for(content, "tag", "h2", index=1))
			self.assertTrue("$20" in get_html_for(content, "tag", "span", index=1))
			self.assertFalse("Item B1" in get_html_for(content, "tag", "h2"))
			self.assertFalse("$15" in get_html_for(content, "tag", "span"))
			self.assertFalse("Item B2" in get_html_for(content, "tag", "h2", index=1))
			self.assertFalse("$25" in get_html_for(content, "tag", "span", index=1))
		finally:
			page.delete()

	def test_set_fonts(self):
		from builder.builder.doctype.builder_page.builder_page import set_fonts

		font_map = {}
		styles = [
			{"fontFamily": "Inter", "fontWeight": "bold"},
			{"fontFamily": "Inter", "fontWeight": 400},
			{"fontFamily": "'Open Sans'", "fontWeight": "600"},
			{"fontFamily": "Impact", "fontWeight": "800"},  # System font, should be skipped
			{"fontFamily": "Inter", "fontWeight": "bold"},  # Duplicate
		]

		set_fonts(styles, font_map)

		self.assertIn("Inter", font_map)
		self.assertIn("Open Sans", font_map)
		self.assertNotIn("Impact", font_map)

		# Weights should be normalized to integers and deduplicated
		self.assertEqual(font_map["Inter"]["weights"], [400, 700])
		self.assertEqual(font_map["Open Sans"]["weights"], [600])

	def test_set_fonts_uses_primary_family_from_fallback_list(self):
		from builder.builder.doctype.builder_page.builder_page import set_fonts

		font_map = {}
		set_fonts([{"fontFamily": "Inter, sans-serif", "fontWeight": "500"}], font_map)

		# Only the first family is requested, not the whole CSS stack
		self.assertIn("Inter", font_map)
		self.assertNotIn("Inter, sans-serif", font_map)

	def test_get_google_font_urls(self):
		from builder.builder.doctype.builder_page.builder_page import get_google_font_urls

		font_map = {
			"Newsreader": {"weights": [500]},
			"Open Sans": {"weights": [700, 400]},
			"Foo & Bar": {"weights": [400]},
		}
		urls = get_google_font_urls(font_map)

		# One combined request per family: 400 always included, weights sorted, family
		# name URL-encoded (spaces -> +, reserved chars escaped so the URL can't break)
		self.assertEqual(
			urls,
			[
				"https://fonts.googleapis.com/css2?family=Newsreader:wght@400;500&display=swap",
				"https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap",
				"https://fonts.googleapis.com/css2?family=Foo+%26+Bar:wght@400&display=swap",
			],
		)

	def test_set_fonts_inherits_font_family_from_ancestor(self):
		"""set_fonts should use inherited_font when a style has fontWeight but no fontFamily."""
		from builder.builder.doctype.builder_page.builder_page import set_fonts

		font_map = {}
		styles = [{"fontWeight": "600"}]

		# Without inherited_font, nothing should be added
		set_fonts(styles, font_map)
		self.assertEqual(font_map, {})

		# With inherited_font, the ancestor font should be registered
		set_fonts(styles, font_map, inherited_font="Newsreader")
		self.assertIn("Newsreader", font_map)
		self.assertIn(600, font_map["Newsreader"]["weights"])

	def test_font_weight_inherited_from_parent_block(self):
		"""Child block with only fontWeight should inherit fontFamily from parent in font_map."""
		from builder.builder.doctype.builder_page.builder_page import get_block_html

		blocks = [
			{
				"element": "div",
				"originalElement": "body",
				"baseStyles": {"fontFamily": "Newsreader"},
				"children": [
					{
						"element": "h1",
						"innerHTML": "Headline",
						"baseStyles": {"fontWeight": "700"},
						"children": [],
					}
				],
			}
		]
		_, _, font_map, _ = get_block_html(blocks)
		self.assertIn("Newsreader", font_map)
		self.assertIn(700, font_map["Newsreader"]["weights"])

	def test_intervar_font_skipped(self):
		"""InterVar should not appear in the font_map — it is loaded via reset.css."""
		from builder.builder.doctype.builder_page.builder_page import get_block_html

		blocks = [
			{
				"element": "div",
				"originalElement": "body",
				"baseStyles": {"fontFamily": "InterVar", "fontWeight": "400"},
				"children": [],
			}
		]
		_, _, font_map, _ = get_block_html(blocks)
		self.assertNotIn("InterVar", font_map)
		self.assertNotIn("intervar", font_map)

	def test_renders_blocks_with_stripped_empty_values(self):
		"""Blocks are saved with empty defaults (attributes={}, classes=[], dataKey=null,
		empty styles, etc.) stripped out to keep documents small"""
		import re

		from builder.builder.doctype.builder_page.builder_page import get_block_html

		def empties():
			return {
				"rawStyles": {},
				"mobileStyles": {},
				"tabletStyles": {},
				"attributes": {},
				"customAttributes": {},
				"classes": [],
				"props": {},
				"dynamicValues": [],
				"dataKey": None,
				"activeState": None,
			}

		full = [
			{
				"blockId": "root",
				"element": "div",
				"originalElement": "body",
				"baseStyles": {"display": "flex"},
				"children": [
					{
						"blockId": "child1",
						"element": "h1",
						"innerHTML": "Hello World!",
						"baseStyles": {"color": "red"},
						"children": [],
						**empties(),
					}
				],
				**empties(),
			}
		]
		stripped = [
			{
				"blockId": "root",
				"element": "div",
				"originalElement": "body",
				"baseStyles": {"display": "flex"},
				"children": [
					{
						"blockId": "child1",
						"element": "h1",
						"innerHTML": "Hello World!",
						"baseStyles": {"color": "red"},
					}
				],
			}
		]

		# CSS class names are a random hash per render (frappe.generate_hash) — ignore them.
		def normalize(text):
			return re.sub(r"[0-9a-f]{8,}", "H", text)

		html_full, css_full, _, _ = get_block_html(full)
		html_stripped, css_stripped, _, _ = get_block_html(stripped)

		self.assertIn("Hello World!", html_stripped)
		self.assertEqual(normalize(html_full), normalize(html_stripped))
		self.assertEqual(normalize(css_full), normalize(css_stripped))

		# A block carrying dynamicValues but with attributes/styles stripped used to
		# raise KeyError in set_dynamic_content_placeholders — guard against regression.
		dynamic = [
			{
				"blockId": "root",
				"element": "div",
				"originalElement": "body",
				"baseStyles": {"display": "flex"},
				"children": [
					{
						"blockId": "img1",
						"element": "img",
						"dynamicValues": [
							{"key": "logo", "type": "attribute", "property": "src", "comesFrom": "dataScript"}
						],
					}
				],
			}
		]
		html_dynamic, _, _, _ = get_block_html(dynamic)
		self.assertIn("logo", html_dynamic)

		with_unset_style = [
			{
				"blockId": "root",
				"element": "div",
				"originalElement": "body",
				"baseStyles": {"color": "red", "display": None},
				"children": [],
			}
		]
		_, css_unset, _, _ = get_block_html(with_unset_style)
		self.assertIn("color: red", css_unset)
		self.assertNotIn("display:", css_unset)
		self.assertNotIn("None", css_unset)

	def test_conflicting_routes_picks_last_published(self):
		"""Pages sharing a route should resolve to the most recently published one."""
		from frappe.utils import add_to_date, now_datetime
		from frappe.website.utils import clear_cache as clear_page_cache

		from builder.builder.doctype.builder_page.builder_page import find_page_with_path

		# Frappe strips leading slashes from routes during validation; use without slash
		route = "conflicting-route-test"

		page_older = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Older Published Page",
				"published": 1,
				"route": route,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[Block(element="h1", innerHTML="Older Published Content")],
				).as_json(wrap_in_array=True),
			}
		).insert()

		page_newer = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Newer Published Page",
				"published": 1,
				"route": route,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[Block(element="h1", innerHTML="Newer Published Content")],
				).as_json(wrap_in_array=True),
			}
		).insert()

		def clear_caches():
			find_page_with_path.clear_cache()
			clear_page_cache(route)

		try:
			page_older.db_set("published_at", add_to_date(now_datetime(), days=-2))
			page_newer.db_set("published_at", add_to_date(now_datetime(), days=-1))
			clear_caches()

			content = get_response_content(f"/{route}")
			self.assertIn("Newer Published Content", content)

			# Republish the older page — it should now be picked
			page_older.db_set("published_at", now_datetime())
			clear_caches()

			content = get_response_content(f"/{route}")
			self.assertIn("Older Published Content", content)
		finally:
			clear_caches()
			page_older.delete()
			page_newer.delete()

	def test_conflicting_routes_no_published_at_picks_last_created(self):
		"""When published_at is absent, the most recently created page should win."""
		from frappe.utils import add_to_date, now_datetime
		from frappe.website.utils import clear_cache as clear_page_cache

		from builder.builder.doctype.builder_page.builder_page import find_page_with_path

		# Frappe strips leading slashes from routes during validation; use without slash
		route = "conflicting-route-no-published-at-test"

		page_first = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "First Created Page",
				"published": 1,
				"route": route,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[Block(element="h1", innerHTML="First Created Content")],
				).as_json(wrap_in_array=True),
			}
		).insert()

		page_second = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Second Created Page",
				"published": 1,
				"route": route,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[Block(element="h1", innerHTML="Second Created Content")],
				).as_json(wrap_in_array=True),
			}
		).insert()

		# Ensure page_first has an older creation timestamp as a tiebreaker
		page_first.db_set("creation", add_to_date(now_datetime(), seconds=-10))

		def clear_caches():
			find_page_with_path.clear_cache()
			clear_page_cache(route)

		try:
			# Both pages have no published_at; creation order should determine the winner
			clear_caches()
			content = get_response_content(f"/{route}")
			self.assertIn("Second Created Content", content)
		finally:
			clear_caches()
			page_first.delete()
			page_second.delete()

	@classmethod
	def tearDownClass(cls):
		cls.page.delete()
		cls.page_with_dynamic_route.delete()


def get_html_for(html, type, value, index=None, only_content=False, list_all=False):
	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, "html.parser")
	if type == "tag":
		results = soup.find_all(value)
		if list_all:
			return [result.decode_contents() if only_content else str(result) for result in results]
		result = (
			results[index] if index is not None and index < len(results) else results[0] if results else None
		)
		if only_content and result:
			return result.decode_contents()
		return str(result) if result else ""
	if type == "attribute":
		results = soup.find_all(attrs={value: True})
		if list_all:
			return [result.get(value) for result in results if result.get(value)]
		result = (
			results[index] if index is not None and index < len(results) else results[0] if results else None
		)
		return result.get(value) if result and result.get(value) else ""
