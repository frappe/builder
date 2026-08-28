import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.query import (
	MAX_PAGE_READS_PER_TURN,
	layout_scaffold,
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
		script = frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"script_type": "CSS",
				"script": ".raven { letter-spacing: 0.08em; }",
			}
		).insert(ignore_permissions=True)
		cls.page.append("client_scripts", {"builder_script": script.name})
		cls.page.save(ignore_permissions=True)

	def ctx(self, page_id="some-other-page", page_read_count=0):
		return SimpleNamespace(page_id=page_id, page_read_count=page_read_count)

	def test_returns_digest_and_structure_for_another_page(self):
		out = run_read_page(self.ctx(), {"page_id": self.page.name})

		self.assertIn("Reference Page", out)
		self.assertIn("READ-ONLY", out)
		self.assertIn("fonts: Libre Baskerville x1 (div), Cinzel x1 (h1)", out)
		self.assertIn("colors: #E6DECA x1, #161412 x1", out)
		self.assertIn("el: h1", out)

	def test_includes_the_pages_attached_scripts(self):
		out = run_read_page(self.ctx(), {"page_id": self.page.name})

		self.assertIn("Attached page scripts", out)
		self.assertIn(".raven { letter-spacing: 0.08em; }", out)

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

	def test_prefers_the_published_page_when_routes_collide(self):
		live = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Live Copy", "route": "collide-route"}
		).insert()
		frappe.db.set_value("Builder Page", live.name, "published", 1, update_modified=False)
		frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Newer Draft", "route": "collide-route"}
		).insert()

		# The draft is more recently modified; the PUBLISHED page still wins —
		# it is the one actually serving the route a reference means.
		self.assertEqual(resolve_page_reference("collide-route")[0], live.name)


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


class TestComponentContract(FrappeTestCase):
	def test_lists_embedded_component_contracts(self):
		component_id = frappe.generate_hash(length=12)
		frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "test-rail",
				"component_id": component_id,
				"block": json.dumps(
					{
						"element": "div",
						"baseStyles": {"width": "fit-content", "display": "flex"},
						"classes": ["hr-sidebar"],
					}
				),
			}
		).insert(ignore_permissions=True)
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Component Host",
				"draft_blocks": json.dumps(
					[
						{
							"element": "div",
							"children": [
								{"element": "div", "extendedFromComponent": component_id, "children": []}
							],
						}
					]
				),
			}
		).insert()

		out = run_read_page(
			SimpleNamespace(page_id="another-page", page_read_count=0), {"page_id": page.name}
		)

		self.assertIn("Embedded components", out)
		self.assertIn("test-rail", out)
		self.assertIn("width: fit-content", out)
		self.assertIn("hr-sidebar", out)

	def test_honours_the_instances_pinned_component_version(self):
		from builder.builder.component_versions import ensure_component_version

		component_id = frappe.generate_hash(length=12)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "pinned-rail",
				"component_id": component_id,
				"block": json.dumps({"element": "div", "baseStyles": {"width": "fit-content"}}),
			}
		).insert(ignore_permissions=True)
		version = ensure_component_version(component_id)
		# db.set_value: the doc is queue-locked by version capture, and only the
		# live column needs to diverge from the snapshot for this test.
		frappe.db.set_value(
			"Builder Component",
			component.name,
			"block",
			json.dumps({"element": "div", "baseStyles": {"width": "999px"}}),
		)
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Pinned Host",
				"draft_blocks": json.dumps(
					[
						{
							"element": "div",
							"children": [
								{
									"element": "div",
									"extendedFromComponent": component_id,
									"componentVersion": version,
									"children": [],
								}
							],
						}
					]
				),
			}
		).insert()

		out = run_read_page(
			SimpleNamespace(page_id="another-page", page_read_count=0), {"page_id": page.name}
		)

		# The page renders the PINNED block, so the contract must state its styles.
		self.assertIn("width: fit-content", out)
		self.assertNotIn("999px", out)

	def test_scaffold_states_the_shell_row_and_rail_component(self):
		root = {
			"element": "div",
			"baseStyles": {"display": "flex", "flexDirection": "row", "alignItems": "stretch"},
			"children": [
				{"element": "div", "extendedFromComponent": "rail-1", "children": []},
				{
					"blockName": "container",
					"element": "div",
					"baseStyles": {"flexDirection": "column", "overflowY": "auto", "width": "100%"},
					"children": [
						{
							"element": "section",
							"baseStyles": {"width": "100%"},
							"children": [{"element": "h1", "baseStyles": {"position": "absolute"}}],
						}
					],
				},
			],
		}

		out = layout_scaffold(root)

		self.assertIn("flexDirection: row", out)
		self.assertIn("[component rail-1]", out)
		self.assertIn("overflowY: auto", out)
		# The h1 sits past SCAFFOLD_DEPTH — content, not shell.
		self.assertNotIn("absolute", out)

	def test_read_page_stashes_geometry_for_the_generation_step(self):
		from builder.ai.agent.artifact import reference_geometry

		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Shell Reference",
				"draft_blocks": json.dumps(
					[
						{
							"element": "div",
							"baseStyles": {"display": "flex", "flexDirection": "row"},
							"children": [],
						}
					]
				),
			}
		).insert()
		ctx = SimpleNamespace(page_id="another-page", page_read_count=0, reference_reads=[])

		run_read_page(ctx, {"page_id": page.name})

		self.assertEqual(len(ctx.reference_reads), 1)
		self.assertIn("Shell Reference", ctx.reference_reads[0])
		message = reference_geometry(ctx)
		self.assertIn("ground truth", message)
		self.assertIn("flexDirection: row", message)
		# A ctx without the stash (tests, older callers) produces no message.
		self.assertEqual(reference_geometry(SimpleNamespace()), "")

	def test_warns_when_a_reference_font_cannot_resolve_on_this_site(self):
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Ghost Font Reference",
				"draft_blocks": json.dumps(
					[
						{
							"element": "div",
							"children": [
								{
									"element": "h1",
									"innerHTML": "Hello",
									"baseStyles": {"fontFamily": "Inter Variable"},
								}
							],
						}
					]
				),
			}
		).insert()
		ctx = SimpleNamespace(page_id="another-page", page_read_count=0, reference_reads=[])

		with patch(
			"builder.ai.agent.tools.query.google_font_exists", side_effect=lambda f: f != "Inter Variable"
		):
			out = run_read_page(ctx, {"page_id": page.name})

		self.assertIn("FONT AVAILABILITY", out)
		self.assertIn("'Inter Variable'", out)
		self.assertIn("Times-like serif", out)
		# The generation step must hear it too, not just the loop model.
		self.assertIn("FONT AVAILABILITY", ctx.reference_reads[0])

	def test_no_font_warning_when_families_resolve(self):
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Resolvable Font Reference",
				"draft_blocks": json.dumps(
					[{"element": "div", "baseStyles": {"fontFamily": "Inter"}, "children": []}]
				),
			}
		).insert()
		ctx = SimpleNamespace(page_id="another-page", page_read_count=0, reference_reads=[])

		with patch("builder.ai.agent.tools.query.google_font_exists", return_value=True):
			out = run_read_page(ctx, {"page_id": page.name})

		self.assertNotIn("FONT AVAILABILITY", out)

	def test_a_user_font_counts_as_available(self):
		from builder.ai.agent.tools.query import unavailable_fonts

		frappe.get_doc({"doctype": "User Font", "font_name": "House Grotesk"}).insert(
			ignore_if_duplicate=True
		)
		root = {"element": "div", "baseStyles": {"fontFamily": "House Grotesk"}, "children": []}

		with patch("builder.ai.agent.tools.query.google_font_exists", return_value=False):
			self.assertEqual(unavailable_fonts(root), [])

	def test_first_prop_override_borrows_the_declared_config(self):
		from builder.ai.agent.tree import merge_props

		component_id = frappe.generate_hash(length=12)
		frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "prop-meta",
				"component_id": component_id,
				"block": json.dumps(
					{
						"element": "div",
						"props": {
							"title": {
								"label": "Title",
								"isDynamic": False,
								"isPassedDown": False,
								"comesFrom": None,
								"propOptions": {"options": {"defaultValue": "Hi"}},
							}
						},
					}
				),
			}
		).insert(ignore_permissions=True)
		instance = {"element": "div", "extendedFromComponent": component_id}

		merge_props(instance, {"title": "Hello"})

		# The value lands INSIDE the declaration's config — label/options survive.
		self.assertEqual(instance["props"]["title"]["value"], "Hello")
		self.assertEqual(instance["props"]["title"]["label"], "Title")

	def test_pinned_empty_schema_cannot_pollute_a_declared_live_schema(self):
		from builder.ai.agent.tree import WorkingTree
		from builder.builder.component_versions import ensure_component_version

		component_id = frappe.generate_hash(length=12)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "pin-guard",
				"component_id": component_id,
				"block": json.dumps({"element": "div", "children": []}),
			}
		).insert(ignore_permissions=True)
		version = ensure_component_version(component_id)
		frappe.db.set_value(
			"Builder Component",
			component.name,
			"block",
			json.dumps({"element": "div", "props": {"title": {"value": "Hi"}}, "children": []}),
		)
		tree = WorkingTree(
			{
				"blockId": "root",
				"element": "div",
				"children": [
					{
						"blockId": "inst",
						"element": "div",
						"extendedFromComponent": component_id,
						"componentVersion": version,
						"children": [],
					}
				],
			}
		)

		# The pinned snapshot has no props, but the LIVE schema does: an unknown
		# name is rejected against the live schema, never declared onto it.
		self.assertIn("FAILED", tree.apply_update("inst", {"props": {"titel": "Typo"}}))
		self.assertIn("Applied", tree.apply_update("inst", {"props": {"title": "New"}}))
		live = frappe.parse_json(frappe.db.get_value("Builder Component", component.name, "block"))
		self.assertEqual(list(live["props"].keys()), ["title"])

	def test_child_targeted_prop_writes_land_on_the_instance_root(self):
		from builder.ai.agent.tree import WorkingTree

		component_id = frappe.generate_hash(length=12)
		frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "prop-route",
				"component_id": component_id,
				"block": json.dumps({"element": "div", "children": []}),
			}
		).insert(ignore_permissions=True)
		tree = WorkingTree(
			{
				"blockId": "root",
				"element": "div",
				"children": [
					{
						"blockId": "inst",
						"element": "div",
						"extendedFromComponent": component_id,
						"children": [
							{
								"blockId": "child",
								"element": "div",
								"isChildOfComponent": component_id,
								"referenceBlockId": "x1",
								"children": [],
							}
						],
					}
				],
			}
		)

		self.assertIn("Applied", tree.apply_update("child", {"props": {"title": "Routed"}}))

		# The canvas routes child prop writes to the instance root (getPropsRoot);
		# the server must land them in the same place or a reload loses the value.
		inst = tree.resolve("inst")
		self.assertEqual(inst["props"]["title"]["value"], "Routed")
		self.assertNotIn("props", tree.resolve("child"))
		self.assertIn("FAILED", tree.apply_update("root", {"props": {"x": "1"}}))

	def test_states_each_pinned_version_when_instances_differ(self):
		from builder.builder.component_versions import ensure_component_version

		component_id = frappe.generate_hash(length=12)
		component = frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_name": "mixed-rail",
				"component_id": component_id,
				"block": json.dumps({"element": "div", "baseStyles": {"width": "fit-content"}}),
			}
		).insert(ignore_permissions=True)
		version = ensure_component_version(component_id)
		frappe.db.set_value(
			"Builder Component",
			component.name,
			"block",
			json.dumps({"element": "div", "baseStyles": {"width": "999px"}}),
		)
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Mixed Pins Host",
				"draft_blocks": json.dumps(
					[
						{
							"element": "div",
							"children": [
								{
									"element": "div",
									"extendedFromComponent": component_id,
									"componentVersion": version,
									"children": [],
								},
								{"element": "div", "extendedFromComponent": component_id, "children": []},
							],
						}
					]
				),
			}
		).insert()

		out = run_read_page(
			SimpleNamespace(page_id="another-page", page_read_count=0), {"page_id": page.name}
		)

		# One instance renders the pinned block, the other the live one — both contracts show.
		self.assertIn("width: fit-content", out)
		self.assertIn("width: 999px", out)
