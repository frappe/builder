from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.edits import EditScript, composition_notes
from builder.ai.agent.tree import ComponentTree, WorkingTree


def page():
	return {
		"blockId": "root",
		"element": "div",
		"children": [
			{
				"blockId": "hero12345",
				"element": "section",
				"baseStyles": {"padding": "96px", "marginTop": "8px"},
				"attributes": {"href": "/x"},
				"children": [{"blockId": "title1234", "element": "h1", "innerHTML": "Hi", "children": []}],
			},
			{"blockId": "footer123", "element": "footer", "children": []},
		],
	}


class TestEditScript(FrappeTestCase):
	def setUp(self):
		self.tree = WorkingTree(page())

	def run_script(self, text, sets=None):
		return EditScript(self.tree, sets).run(text)

	def ids(self, block_id="root"):
		return [c["blockId"] for c in self.tree.resolve(block_id)["children"]]

	def test_a_patch_merges_removes_and_renames(self):
		report, ops = self.run_script('@hero {padding:40px;margin-top:} [-href] "New" // Hero')

		hero = self.tree.resolve("hero12345")
		self.assertEqual(hero["baseStyles"], {"padding": "40px"})
		self.assertNotIn("href", hero["attributes"])
		self.assertEqual((hero["innerHTML"], hero["blockName"]), ("New", "Hero"))
		self.assertEqual(ops[0]["tool_name"], "update_block")
		self.assertEqual(ops[0]["args"]["block_id"], "hero12345")
		self.assertEqual(report, "Applied 1 op(s).")

	def test_the_mirrored_patch_carries_normalized_styles(self):
		_, ops = self.run_script("@hero {padding:40;justify-content:spaceBetween}")

		self.assertEqual(
			ops[0]["args"]["base_styles"], {"padding": "40px", "justifyContent": "space-between"}
		)

	def test_a_patch_that_pads_a_full_width_block_mirrors_border_box(self):
		_, ops = self.run_script("@hero {width:100%;padding:40px 48px}")

		self.assertEqual(self.tree.resolve("hero12345")["baseStyles"]["boxSizing"], "border-box")
		self.assertEqual(ops[0]["args"]["base_styles"]["boxSizing"], "border-box")

	def test_several_refs_take_one_patch(self):
		_, ops = self.run_script("@hero @foot {color:red}")

		self.assertEqual([op["args"]["block_id"] for op in ops], ["hero12345", "footer123"])

	def test_add_after_places_every_new_sibling_in_order(self):
		report, ops = self.run_script('add after @hero\n  section "a"\n  section "b"')

		new = self.ids()[1:3]
		self.assertEqual([self.tree.resolve(i)["innerHTML"] for i in new], ["a", "b"])
		self.assertEqual([op["args"]["index"] for op in ops], [1, 2])
		self.assertIn("New blocks", report)
		self.assertIn('"a"', report)

	def test_add_into_a_parent_at_an_index_and_appended(self):
		self.run_script('add @hero 0\n  p "first"\nadd @hero\n  p "last"')

		texts = [self.tree.resolve(i).get("innerHTML") for i in self.ids("hero12345")]
		self.assertEqual(texts, ["first", "Hi", "last"])

	def test_add_carries_scripts_as_a_follow_up_patch(self):
		self.tree = ComponentTree(page(), "comp")

		_, ops = self.run_script("add @foot\n  div\n    js |\n      this.remove();")

		self.assertEqual([op["tool_name"] for op in ops], ["add_block", "update_block"])
		self.assertEqual(ops[1]["args"]["client_script"], {"js": "this.remove();"})

	def test_replace_keeps_the_position(self):
		self.run_script('replace @hero\n  section "fresh"')

		first = self.tree.resolve(self.ids()[0])
		self.assertEqual((first["innerHTML"], len(self.ids())), ("fresh", 2))

	def test_move_before_and_after(self):
		self.run_script("move @foot before @hero")
		self.assertEqual(self.ids(), ["footer123", "hero12345"])

		self.run_script("move @foot after @hero")
		self.assertEqual(self.ids(), ["hero12345", "footer123"])

		self.run_script("move @title to @foot")
		self.assertEqual(self.ids("footer123"), ["title1234"])

	def test_remove(self):
		self.run_script("remove @foot")

		self.assertEqual(self.ids(), ["hero12345"])

	def test_the_root_cannot_be_removed_replaced_or_a_sibling_target(self):
		report, ops = self.run_script('remove @root\nreplace @root\n  div\nadd after @root\n  p "x"')

		self.assertEqual(ops, [])
		self.assertEqual(report.count("FAILED"), 3)

	def test_a_failure_names_its_line_and_the_rest_apply(self):
		report, ops = self.run_script('@nope {color:red}\n@hero "ok"\n@title {broken')

		self.assertIn("Applied 1 of 3 op(s).", report)
		self.assertIn("FAILED line 1: @nope not found", report)
		self.assertIn("FAILED line 3:", report)
		self.assertEqual(len(ops), 1)

	def test_an_ambiguous_ref_lists_candidates(self):
		self.tree.resolve("footer123")["children"].append({"blockId": "hero9zzzz", "element": "p"})

		report, _ = self.run_script("@hero {color:red}")

		self.assertIn("matches 2 blocks", report)

	def test_a_set_from_the_last_read_spreads_into_a_new_block(self):
		self.run_script('add @foot\n  p $s1 "x"', sets={"s1": {"style": {"fontSize": "11px"}}})

		added = self.tree.resolve(self.ids("footer123")[0])
		self.assertEqual(added["baseStyles"], {"fontSize": "11px"})

	def test_an_icon_patch_rebakes_the_svg(self):
		_, ops = self.run_script("@title icon(star)")

		self.assertEqual(ops[0]["args"]["attributes"], {"data-lucide": "star"})
		self.assertIn("<svg", self.tree.resolve("title1234")["innerHTML"])


class TestCompositionNotes(FrappeTestCase):
	def test_flags_an_absolute_block_under_an_unpositioned_parent(self):
		root = page()
		root["children"].insert(
			0, {"blockId": "photo1234", "element": "img", "baseStyles": {"position": "absolute"}}
		)

		self.assertIn("@phot", composition_notes(root))

	def test_a_positioned_parent_is_fine(self):
		root = page()
		hero = root["children"][0]
		hero["baseStyles"]["position"] = "relative"
		hero["children"].append(
			{"blockId": "scrim1234", "element": "div", "baseStyles": {"position": "absolute"}}
		)

		self.assertEqual(composition_notes(root), "")

	def test_flags_eyebrows_past_the_one_a_page_allows(self):
		def label(block_id):
			return {
				"blockId": block_id,
				"element": "p",
				"innerHTML": "THE MENU",
				"baseStyles": {"textTransform": "uppercase", "fontSize": "11px"},
			}

		heading = {"blockId": "headline1", "element": "h2", "innerHTML": "Bowls"}
		root = {
			"blockId": "root",
			"children": [{"blockId": "sec11111", "children": [label("eyebrow1"), heading]}],
		}
		self.assertEqual(composition_notes(root), "")

		root["children"].append(
			{"blockId": "sec22222", "children": [label("eyebrow2"), {**heading, "blockId": "headline2"}]}
		)
		self.assertIn("AI TELL: 2 headings", composition_notes(root))

		root["children"][1]["children"][0]["baseStyles"]["display"] = "none"
		self.assertEqual(composition_notes(root), "")


class TestClosingReply(FrappeTestCase):
	def reply(self, ops, results):
		from builder.ai.agent.loop import AgentRunner

		return AgentRunner.closing_reply(ops, results)

	def edit(self, reply=None):
		return {
			"tool_name": "edit_page",
			"args": {"ops": "@a {color:red}", **({"reply": reply} if reply else {})},
		}

	def test_a_landed_edit_with_a_reply_ends_the_turn(self):
		self.assertEqual(self.reply([self.edit("Made it red.")], ["Applied 1 op(s)."]), "Made it red.")

	def test_no_reply_a_failure_or_a_read_in_the_round_keeps_going(self):
		self.assertEqual(self.reply([self.edit()], ["Applied 1 op(s)."]), "")
		self.assertEqual(
			self.reply([self.edit("Done.")], ["Applied 0 of 1 op(s).\nFAILED line 1: @a not found"]), ""
		)
		preview = {"tool_name": "preview_page", "args": {}}
		self.assertEqual(
			self.reply([self.edit("Done."), preview], ["Applied 1 op(s).", "Screenshot attached"]), ""
		)

	def test_a_reply_waits_for_a_preview_of_a_page_built_this_turn(self):
		from builder.ai.agent.loop import AgentRunner

		runner = AgentRunner("hi", model="m", api_key="k")
		runner.unreviewed_build = True
		self.assertEqual(runner.turn_reply([self.edit("Done.")], ["Applied 1 op(s)."]), "")
		runner.unreviewed_build = False
		self.assertEqual(runner.turn_reply([self.edit("Done.")], ["Applied 1 op(s)."]), "Done.")

	def test_dropped_generation_lines_are_named_to_the_model(self):
		from builder.ai.agent.loop import AgentRunner

		runner = AgentRunner("hi", model="m", api_key="k")
		self.assertEqual(runner.dropped_lines_note(), "")
		runner.generation_errors = ["line 45: unexpected text at `Morning`"]
		self.assertIn("DROPPED LINES: 1 line(s)", runner.dropped_lines_note())
