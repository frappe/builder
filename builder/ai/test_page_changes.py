import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import llm
from builder.ai.agent.edits import EditScript
from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.page_changes import PageChanges, apply_page_changes
from builder.ai.api import confirm_pending_settings
from builder.ai.page_writer import load_page_root
from builder.ai.session import AISession


def make_page(title: str, route: str, children: list, folder: str = "") -> str:
	root = {"blockId": "root", "element": "div", "originalElement": "body", "children": children}
	return (
		frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": title,
				"route": route,
				"project_folder": folder,
				"draft_blocks": json.dumps([root]),
			}
		)
		.insert()
		.name
	)


def heading(block_id: str, text: str) -> dict:
	return {"blockId": block_id, "element": "h1", "innerHTML": text, "baseStyles": {}}


def texts(page_id: str) -> dict:
	return {c["blockId"]: c.get("innerHTML") for c in load_page_root(page_id)["children"]}


def chunk(content=None, tool_calls=None, finish_reason=None):
	delta = SimpleNamespace(content=content, tool_calls=tool_calls, reasoning_content=None)
	return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish_reason)], usage=None)


def tool_call(name: str, args: dict, index: int = 0):
	function = SimpleNamespace(name=name, arguments=json.dumps(args))
	return SimpleNamespace(index=index, id=f"call_{name}_{index}", function=function)


class ScriptedModel:
	"""Answers each tool round with the next scripted step: tool calls, or a reply."""

	def __init__(self, *rounds):
		self.rounds = list(rounds)

	def __call__(self, *args, **kwargs):
		step = self.rounds.pop(0)
		if isinstance(step, str):
			return iter([chunk(content=step, finish_reason="stop")])
		calls = [tool_call(name, args, i) for i, (name, args) in enumerate(step)]
		return iter([chunk(tool_calls=calls, finish_reason="tool_calls")])


class TestPageChanges(FrappeTestCase):
	def setUp(self):
		self.open_page = make_page("Home", "mp-home", [heading("homehead1", "Welcome")], folder="")
		self.other = make_page(
			"About", "mp-about", [heading("abouthead1", "About us"), heading("aboutfoot1", "© 2024")]
		)

	def test_an_edit_to_another_page_is_checked_but_not_saved(self):
		changes = PageChanges()

		content, lines = changes.edit(self.other, '@abouthead1 "Our story"', {})

		self.assertIn("NOT APPLIED YET", content)
		self.assertEqual(lines, ["Change “About us” to “Our story”"])
		self.assertEqual(texts(self.other)["abouthead1"], "About us")
		self.assertEqual(changes.tree_of(self.other).resolve("abouthead1")["innerHTML"], "Our story")

	def test_a_bad_ref_comes_back_and_holds_nothing(self):
		changes = PageChanges()

		content, lines = changes.edit(self.other, '@nosuchblock "x"', {})

		self.assertIn("FAILED", content)
		self.assertEqual(lines, [])
		self.assertFalse(changes)

	def test_checking_an_edit_writes_nothing_even_when_a_tool_would(self):
		def write_then_report(script, text):
			frappe.db.set_value("Builder Page", self.open_page, "page_title", "Written while checking")
			return "Applied 0 op(s).", []

		with patch.object(EditScript, "run", write_then_report):
			PageChanges().edit(self.other, "@abouthead1 {color:red}", {})

		self.assertEqual(frappe.db.get_value("Builder Page", self.open_page, "page_title"), "Home")

	def test_apply_lands_the_edit_on_the_page_as_it_is_now(self):
		changes = PageChanges()
		changes.edit(self.other, '@abouthead1 "Our story"', {})
		root = load_page_root(self.other)
		root["children"][1]["innerHTML"] = "© 2026"  # the user edited meanwhile
		frappe.db.set_value("Builder Page", self.other, "draft_blocks", json.dumps([root]))

		outcome, results = apply_page_changes(changes.payload())

		self.assertEqual(texts(self.other), {"abouthead1": "Our story", "aboutfoot1": "© 2026"})
		self.assertEqual(results[0]["status"], "changed")
		self.assertIn("Changed “About” (/mp-about)", outcome)
		self.assertTrue(
			frappe.db.exists("Builder Snapshot", {"reference_name": self.other, "snapshot_type": "AI"})
		)

	def test_apply_leaves_a_page_alone_when_its_block_is_gone(self):
		changes = PageChanges()
		changes.edit(self.other, '@abouthead1 "Our story"', {})
		root = load_page_root(self.other)
		root["children"] = root["children"][1:]
		frappe.db.set_value("Builder Page", self.other, "draft_blocks", json.dumps([root]))

		outcome, results = apply_page_changes(changes.payload())

		self.assertEqual(results[0]["status"], "failed")
		self.assertIn("changed after I read it (a block it changes is gone)", results[0]["detail"])
		self.assertIn("nothing was changed there", outcome)
		self.assertEqual(texts(self.other), {"aboutfoot1": "© 2024"})

	def test_blocks_added_while_checking_keep_their_ids_for_later_edits(self):
		changes = PageChanges()
		changes.edit(self.other, 'add @root\n  p "Fresh"', {})
		added = changes.tree_of(self.other).root["children"][-1]["blockId"]
		changes.edit(self.other, f"@{added} {{color:#123456}}", {})

		apply_page_changes(changes.payload())

		block = load_page_root(self.other)["children"][-1]
		self.assertEqual((block["blockId"], block["innerHTML"]), (added, "Fresh"))
		self.assertEqual(block["baseStyles"]["color"], "#123456")

	def test_a_new_page_is_proposed_then_created_in_the_open_pages_folder(self):
		folder = frappe.get_doc({"doctype": "Builder Project Folder", "folder_name": "MP Site"}).insert().name
		changes = PageChanges(folder)

		self.assertIn("FAILED", changes.propose_page("Dup", "mp-about", "x"))
		self.assertIn("PROPOSED, NOT CREATED", changes.propose_page("Careers", "/mp-careers/", "Open roles"))
		self.assertFalse(frappe.db.exists("Builder Page", {"route": "mp-careers"}))

		_, results = apply_page_changes(changes.payload())

		page = frappe.db.get_value(
			"Builder Page", results[0]["page_id"], ["page_title", "route", "project_folder"], as_dict=True
		)
		self.assertEqual(
			(page.page_title, page.route, page.project_folder), ("Careers", "mp-careers", folder)
		)
		self.assertEqual((results[0]["status"], results[0]["brief"]), ("created", "Open roles"))

	def test_a_route_taken_before_the_ok_fails_only_that_page(self):
		changes = PageChanges()
		changes.propose_page("Careers", "mp-jobs", "Open roles")
		changes.edit(self.other, '@abouthead1 "Our story"', {})
		make_page("Jobs", "mp-jobs", [])

		_, results = apply_page_changes(changes.payload())

		self.assertEqual([r["status"] for r in results], ["failed", "changed"])
		self.assertIn("taken meanwhile", results[0]["detail"])


class TestPageChangesInATurn(FrappeTestCase):
	"""A turn checkpoints (commits) as it goes, so its pages outlive the test: every
	route is unique to the run."""

	def setUp(self):
		self.tag = frappe.generate_hash(length=6)
		self.open_page = make_page("Home", f"mpt-home-{self.tag}", [heading("homehead2", "Welcome")])
		self.other = make_page("About", f"mpt-about-{self.tag}", [heading("abouthead2", "About us")])
		self.session_id = AISession.create({"page": self.open_page}).name
		self.events = []

	def run_turn(self, *rounds, **runner_kwargs):
		runner = AgentRunner(
			"change the about page",
			"m",
			"k",
			page_id=self.open_page,
			session_id=self.session_id,
			**runner_kwargs,
		)
		record = lambda event, message, **kwargs: self.events.append((event, message))  # noqa: E731
		with (
			patch.object(llm, "complete_with_tools", ScriptedModel(*rounds)),
			patch("frappe.publish_realtime", record),
			patch.object(AgentRunner, "maybe_name_session"),
		):
			runner.run()
		return runner

	def messages(self) -> list[dict]:
		return AISession.get(self.session_id).get_messages()

	def test_a_turn_ends_with_one_card_for_its_other_page_edits(self):
		self.run_turn(
			[("edit_page", {"page": f"mpt-about-{self.tag}", "ops": '@abouthead2 "Our story"'})],
			"I've prepared the new heading for About; apply it below.",
		)

		self.assertEqual(texts(self.other)["abouthead2"], "About us")
		reply, card = self.messages()[-2:]
		self.assertEqual(reply["content"], "I've prepared the new heading for About; apply it below.")
		self.assertEqual(
			(card["metadata"]["status"], card["metadata"]["kind"]), ("pending_action", "page_changes")
		)
		self.assertEqual(card["metadata"]["payload"]["pages"][0]["page_id"], self.other)
		self.assertIn(f"“About” (/mpt-about-{self.tag}): Change “About us” to “Our story”", card["content"])
		steps = [m for e, m in self.events if e.startswith("ai_chat_step") and m.get("tool") == "edit_page"]
		self.assertEqual(steps[0]["summary"], "Preparing changes to About")
		self.assertEqual(steps[-1]["summary"], "Prepared for About: Change “About us” to “Our story”")
		self.assertFalse([e for e, _ in self.events if e.startswith("ai_chat_tool_batch")])

	def test_the_editors_changed_blocks_land_on_the_reply_not_the_card(self):
		self.run_turn([("edit_page", {"page": self.other, "ops": '@abouthead2 "Our story"'})], "Ready.")

		AISession.get(self.session_id).update_last_assistant_metadata({"affectedBlocks": [{"block_id": "x"}]})

		reply, card = self.messages()[-2:]
		self.assertEqual(reply["metadata"]["affectedBlocks"], [{"block_id": "x"}])
		self.assertNotIn("affectedBlocks", card["metadata"])

	def test_a_question_card_waits_until_the_held_edits_are_shown(self):
		runner = AgentRunner("x", "m", "k", page_id=self.open_page, session_id=self.session_id)
		runner.page_changes.edit(self.other, '@abouthead2 "Our story"', {})

		declined = runner.handle_terminal({"tool_name": "present_ui", "args": {"text": "Which?"}})

		self.assertIn("FAILED", declined)

	def test_confirming_the_card_applies_it_and_lists_each_page(self):
		self.run_turn([("edit_page", {"page": self.other, "ops": '@abouthead2 "Our story"'})], "Ready.")
		card = self.messages()[-1]

		with patch("frappe.enqueue") as enqueue:
			result = confirm_pending_settings(card["id"], "apply")

		self.assertEqual(texts(self.other)["abouthead2"], "Our story")
		self.assertFalse(result["resumed"])
		enqueue.assert_not_called()
		card, outcome = self.messages()[-2:]
		self.assertEqual(card["metadata"]["results"][0]["status"], "changed")
		self.assertEqual(outcome["metadata"]["card"], card["id"])
		self.assertEqual(frappe.db.get_value("Builder AI Message", card["id"], "status"), "action_applied")

	def test_skipping_the_card_changes_nothing_and_starts_no_turn(self):
		self.run_turn([("edit_page", {"page": self.other, "ops": '@abouthead2 "Our story"'})], "Ready.")

		with patch("frappe.enqueue") as enqueue:
			result = confirm_pending_settings(self.messages()[-1]["id"], "skip")

		self.assertEqual((result["status"], result["resumed"]), ("skipped", False))
		enqueue.assert_not_called()
		self.assertEqual(texts(self.other)["abouthead2"], "About us")

	def test_a_created_page_is_built_next_off_the_open_canvas(self):
		self.run_turn(
			[
				(
					"create_page",
					{"title": "Careers", "route": f"mpt-careers-{self.tag}", "brief": "Open roles"},
				)
			],
			"Shall I?",
		)

		with patch("frappe.enqueue") as enqueue, patch("builder.ai.api.resolve_api_key"):
			result = confirm_pending_settings(self.messages()[-1]["id"], "apply")

		created = result["pages"][0]["page_id"]
		job = enqueue.call_args.kwargs
		self.assertTrue(result["resumed"])
		self.assertEqual(
			(job["page_id"], job["open_page_id"], job["next_builds"]), (created, self.open_page, [])
		)
		self.assertIn("Open roles", job["prompt"])

	def test_a_build_turn_sends_canvas_events_to_its_own_page(self):
		new_page = make_page("Careers", f"mpt-built-{self.tag}", [heading("careerhead", "Careers")])
		runner = AgentRunner(
			"build", "m", "k", page_id=new_page, open_page_id=self.open_page, session_id=self.session_id
		)
		with patch(
			"frappe.publish_realtime", lambda event, message, **kw: self.events.append((event, message))
		):
			runner.emit_to_page("tool_batch", operations=[])
			runner.emit("step", id=0)

		self.assertTrue(runner.off_screen)
		self.assertEqual(
			[(e, m["page_id"]) for e, m in self.events],
			[
				(f"ai_chat_tool_batch_{new_page}", new_page),
				(f"ai_chat_step_{self.open_page}", self.open_page),
			],
		)
		self.assertIn("Working page: 'Careers'", runner.build_open_page_context())

	def test_a_build_turn_hands_on_the_next_approved_page(self):
		builds = [{"page_id": self.other, "title": "About", "route": "/about", "brief": "b"}]

		with patch("builder.ai.api.queue_page_build") as queue:
			self.run_turn("Built it.", next_builds=builds)

		queue.assert_called_once_with(self.session_id, builds, "Administrator")
