from unittest import skipUnless
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request

from builder.draft_api import DRAFT_ROLE, create_page, preview, save_page
from builder.utils import compact_json

try:
	from frappe.mcp.tools import call as call_mcp
except ImportError:
	call_mcp = None


def tree(text):
	return [
		{
			"blockId": "root",
			"element": "div",
			"originalElement": "body",
			"children": [{"blockId": "heading", "element": "h1", "innerHTML": text}],
		}
	]


class TestDraftAPI(FrappeTestCase):
	def setUp(self):
		self.agent = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"draft-{frappe.generate_hash(length=8)}@example.com",
					"first_name": "Draft Agent",
					"send_welcome_email": 0,
					"roles": [{"role": DRAFT_ROLE}],
				}
			)
			.insert()
			.name
		)
		self.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Draft API test",
				"published": 1,
				"blocks": compact_json(tree("Published heading")),
				"draft_blocks": compact_json(tree("Previous draft")),
			}
		).insert()
		set_request(method="POST", path="/api/v2/mcp")

	def test_save_snapshots_working_content_and_leaves_live_fields_unchanged(self):
		before = self.page.as_dict()
		with self.set_user(self.agent):
			result = save_page(self.page.name, tree("New draft"), str(self.page.modified))
		self.page.reload()
		self.assertEqual(frappe.parse_json(self.page.draft_blocks), tree("New draft"))
		for field in ("blocks", "published", "staging", "route", "page_data_script", "preview"):
			self.assertEqual(self.page.get(field), before.get(field), field)
		snapshot = frappe.get_doc("Builder Snapshot", result["snapshot"])
		self.assertEqual(
			frappe.parse_json(snapshot.data),
			{
				"blocks": before.blocks,
				"draft_blocks": before.draft_blocks,
			},
		)
		self.assertEqual(result["modified"], str(self.page.modified))
		self.assertIn("/api/method/builder.draft_api.preview?page=", result["preview_url"])

	def test_snapshot_falls_back_to_live_tree_when_there_was_no_draft(self):
		self.page.draft_blocks = None
		self.page.save()
		with self.set_user(self.agent):
			result = save_page(self.page.name, tree("First draft"), str(self.page.modified))
		snapshot = frappe.get_doc("Builder Snapshot", result["snapshot"])
		data = frappe.parse_json(snapshot.data)
		self.assertEqual(frappe.parse_json(data["draft_blocks"] or data["blocks"]), tree("Published heading"))

	def test_stale_write_does_not_overwrite_a_human_edit_or_create_a_snapshot(self):
		modified = str(self.page.modified)
		self.page.draft_blocks = compact_json(tree("Human edit"))
		self.page.save()
		with self.set_user(self.agent), self.assertRaises(frappe.TimestampMismatchError):
			save_page(self.page.name, tree("Stale edit"), modified)
		self.page.reload()
		self.assertEqual(frappe.parse_json(self.page.draft_blocks), tree("Human edit"))
		self.assertFalse(frappe.db.exists("Builder Snapshot", {"reference_name": self.page.name}))

	def test_create_page_reuses_scripts_without_editing_them_or_publishing(self):
		script = frappe.get_doc(
			{"doctype": "Builder Client Script", "script_type": "JavaScript", "script": "// configured form"}
		).insert()
		self.page.page_data_script = 'data.message = "Existing data"'
		self.page.append("client_scripts", {"builder_script": script.name})
		self.page.save()
		with self.set_user(self.agent):
			result = create_page("New landing page", tree("New page"), self.page.name)
		page = frappe.get_doc("Builder Page", result["page"])
		self.assertFalse(page.published)
		self.assertFalse(page.staging)
		self.assertEqual(frappe.parse_json(page.blocks), [])
		self.assertEqual(frappe.parse_json(page.draft_blocks), tree("New page"))
		self.assertEqual(page.page_data_script, self.page.page_data_script)
		self.assertEqual([row.builder_script for row in page.client_scripts], [script.name])
		self.assertEqual(
			str(frappe.get_doc("Builder Client Script", script.name).modified), str(script.modified)
		)
		self.assertNotEqual(page.route, self.page.route)

	def test_role_has_reads_but_no_general_document_write_or_publish_permission(self):
		with self.set_user(self.agent):
			for doctype in (
				"Builder Page",
				"Builder Component",
				"Builder Token",
				"Builder Client Script",
				"User Font",
			):
				self.assertTrue(frappe.has_permission(doctype, "read"), doctype)
				for operation in ("create", "write", "delete", "share"):
					self.assertFalse(frappe.has_permission(doctype, operation), (doctype, operation))
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Builder Page", self.page.name).publish()
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Builder Page", self.page.name).save()

	def test_an_unprivileged_user_cannot_call_the_draft_methods(self):
		with self.set_user("Guest"):
			with self.assertRaises(frappe.PermissionError):
				create_page("Forbidden", tree("Forbidden"))
			with self.assertRaises(frappe.PermissionError):
				save_page(self.page.name, tree("Forbidden"), str(self.page.modified))
			with self.assertRaises(frappe.PermissionError):
				preview(self.page.name)

	def test_rejects_malformed_trees_before_saving(self):
		with self.set_user(self.agent):
			for blocks in ([], ["not a block"], [{"children": {}}], [{"children": [None]}]):
				with self.subTest(blocks=blocks), self.assertRaises((frappe.ValidationError, TypeError)):
					save_page(self.page.name, blocks, str(self.page.modified))
		self.assertFalse(frappe.db.exists("Builder Snapshot", {"reference_name": self.page.name}))

	def test_user_permissions_restrict_edits_source_pages_and_previews(self):
		allowed = frappe.get_doc({"doctype": "Builder Page", "page_title": "Allowed page"}).insert()
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": self.agent,
				"allow": "Builder Page",
				"for_value": allowed.name,
				"apply_to_all_doctypes": 1,
			}
		).insert()
		with self.set_user(self.agent):
			with self.assertRaises(frappe.PermissionError):
				save_page(self.page.name, tree("Forbidden"), str(self.page.modified))
			with self.assertRaises(frappe.PermissionError):
				create_page("Forbidden source", tree("New page"), self.page.name)
			with self.assertRaises(frappe.PermissionError):
				preview(self.page.name)

	def test_standard_pages_cannot_be_changed_through_the_draft_api(self):
		frappe.db.set_value("Builder Page", self.page.name, "is_standard", 1)
		self.page.reload()
		with self.set_user(self.agent), self.assertRaises(frappe.ValidationError):
			save_page(self.page.name, tree("Forbidden"), str(self.page.modified))

	def test_preview_renders_draft_without_generating_a_published_thumbnail(self):
		with self.set_user(self.agent), patch("frappe.enqueue_doc") as enqueue:
			response = preview(self.page.name)
		self.assertIn("Previous draft", response.get_data(as_text=True))
		self.assertNotIn("Published heading", response.get_data(as_text=True))
		self.assertEqual(response.headers["Cache-Control"], "private, no-store")
		enqueue.assert_not_called()

	@skipUnless(call_mcp, "Built-in MCP requires Frappe v16")
	def test_mcp_can_call_the_draft_api_but_not_general_writes_or_publish(self):
		from frappe.api.discovery import build_cache

		build_cache()
		with self.set_user(self.agent):
			schema = call_mcp(
				{
					"name": "get_method_schema",
					"arguments": {"method": "builder.draft_api.save_page"},
				}
			)
			self.assertFalse(schema["isError"])
			self.assertEqual(
				[param["name"] for param in schema["structuredContent"]["params"]],
				["page", "blocks", "modified"],
			)
			result = call_mcp(
				{
					"name": "call_method",
					"arguments": {
						"method": "builder.draft_api.save_page",
						"args": {
							"page": self.page.name,
							"blocks": tree("MCP draft"),
							"modified": str(self.page.modified),
						},
					},
				}
			)
			self.assertFalse(result["isError"])
			with self.assertRaises(frappe.PermissionError):
				call_mcp(
					{
						"name": "update_document",
						"arguments": {
							"doctype": "Builder Page",
							"name": self.page.name,
							"data": {"blocks": compact_json(tree("Forbidden"))},
						},
					}
				)
			with self.assertRaises(frappe.PermissionError):
				call_mcp(
					{
						"name": "call_document_method",
						"arguments": {
							"doctype": "Builder Page",
							"name": self.page.name,
							"method": "publish",
						},
					}
				)
		self.page.reload()
		self.assertEqual(frappe.parse_json(self.page.draft_blocks), tree("MCP draft"))
		self.assertEqual(frappe.parse_json(self.page.blocks), tree("Published heading"))
