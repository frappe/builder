import json

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.editor_demo import CONTENT_SECURITY_POLICY, EditorDemo


def insert(doctype, **fields):
	return frappe.get_doc({"doctype": doctype, **fields}).insert(ignore_permissions=True)


class TestEditorDemo(FrappeTestCase):
	def setUp(self):
		self.component = insert(
			"Builder Component",
			component_name="Demo Card",
			block=json.dumps({"blockId": "card", "element": "div"}),
			component_data_script="data.update({'secret': 'component'})",
		)
		self.script = insert(
			"Builder Client Script",
			name=f"demo-script-{frappe.generate_hash(length=6)}",
			script_type="JavaScript",
			script="console.log('hello from the page')",
		)
		self.token = insert("Builder Token", token_name="demo-ink", value="#111111")
		self.unused_token = insert("Builder Token", token_name="demo-unused", value="#222222")
		cta = {"blockId": "cta", "element": "a", "baseStyles": {"color": f"var(--{self.token.name})"}}
		card = {"blockId": "card", "element": "div", "extendedFromComponent": self.component.name}
		self.blocks = [{"blockId": "root", "element": "div", "children": [cta, card]}]
		self.page = insert(
			"Builder Page",
			page_title="Editor Demo",
			route=f"editor-demo-{frappe.generate_hash(length=6)}",
			published=1,
			blocks=json.dumps(self.blocks),
			draft_blocks=json.dumps([{"blockId": "root", "element": "div", "innerHTML": "unpublished"}]),
			page_data_script="data.update({'secret': 'page'})",
			client_scripts=[{"builder_script": self.script.name}],
		)
		frappe.conf.builder_demo_pages = [self.page.name]

	def tearDown(self):
		frappe.conf.pop("builder_demo_pages", None)
		frappe.db.rollback()

	def open_demo(self):
		return EditorDemo.from_app_path(f"demo/{self.page.name}")

	def test_leaves_other_editor_routes_alone(self):
		self.assertIsNone(EditorDemo.from_app_path(None))
		self.assertIsNone(EditorDemo.from_app_path(f"page/{self.page.name}"))

	def test_refuses_pages_that_are_not_public_and_opted_in(self):
		frappe.conf.builder_demo_pages = []
		self.assertRaises(frappe.PageDoesNotExistError, self.open_demo)
		frappe.conf.builder_demo_pages = [self.page.name]
		for field, value in {"published": 0, "authenticated_access": 1}.items():
			with self.subTest(field=field):
				frappe.db.set_value("Builder Page", self.page.name, field, value)
				self.assertRaises(frappe.PageDoesNotExistError, self.open_demo)
				frappe.db.set_value("Builder Page", self.page.name, field, int(not value))

	def test_carries_only_what_the_published_page_renders(self):
		payload = self.open_demo().build_payload()

		self.assertEqual(json.loads(payload["page"]["blocks"]), self.blocks)
		self.assertNotIn("draft_blocks", payload["page"])
		self.assertEqual([script.script for script in payload["scripts"]], [self.script.script])
		self.assertEqual(list(payload["components"]), [self.component.name])
		self.assertEqual([token.name for token in payload["tokens"]], [self.token.name])
		self.assertNotIn("secret", frappe.as_json(payload))
		self.assertNotIn("unpublished", frappe.as_json(payload))

	def test_shell_has_no_session_and_no_way_out(self):
		context = frappe._dict()
		self.open_demo().set_context(context)

		self.assertEqual(context.csrf_token, "")
		self.assertEqual(context.is_developer_mode, 0)
		self.assertEqual(frappe.local.response_headers["Content-Security-Policy"], CONTENT_SECURITY_POLICY)
		for directive in (
			"connect-src https://fonts.googleapis.com;",
			"frame-ancestors 'self'",
			"form-action 'none'",
			"base-uri 'none'",
		):
			self.assertIn(directive, CONTENT_SECURITY_POLICY)
