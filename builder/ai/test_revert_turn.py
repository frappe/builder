"""Reverting an AI turn (restore_snapshot on its pre-turn "AI" snapshot) puts the page's draft back. The live
page runs the page's client scripts and data script as they are, so a revert puts those back only while the
turn's work is not live: once Bob published it (publish_page) or someone did after the turn, the live page keeps
the turn's blocks until the restored draft is published, and it keeps the scripts those blocks rely on."""

import glob
import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_files_path

from builder.ai.agent.loop import AgentRunner
from builder.ai.snapshots import capture_page_state, save_revert_snapshot
from builder.builder.tests.hosting_hooks import hosting_hooks, without_save_hooks

KEPT_LIVE = "This AI edit was already published"


def tree(*texts: str) -> str:
	children = [
		{"blockId": f"text{i}", "element": "h1", "innerHTML": text, "baseStyles": {}}
		for i, text in enumerate(texts)
	]
	return json.dumps(
		[{"blockId": "root", "element": "div", "originalElement": "body", "children": children}]
	)


class TestRevertTurn(FrappeTestCase):
	def setUp(self):
		super().setUp()
		# Builder's own revert, whatever an installed host refuses on save (frappe.page's own site refuses
		# client scripts and data scripts outright)
		self.enterContext(without_save_hooks())
		self.tag = frappe.generate_hash(length=6)
		self.before = self.script("show('before')")
		self.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Revert",
				"route": f"revert-{self.tag}",
				"draft_blocks": tree("Old"),
				"page_data_script": "data.plans = ['old']",
				"client_scripts": [{"builder_script": self.before}],
			}
		).insert()

	def script(self, content: str) -> str:
		name = f"revert-{self.tag}-{frappe.generate_hash(length=4)}"
		self.addCleanup(remove_script_files, name)
		doc = {
			"doctype": "Builder Client Script",
			"name": name,
			"script_type": "JavaScript",
			"script": content,
		}
		return frappe.get_doc(doc).insert().name

	def run_turn(self) -> str:
		"""A turn as Bob's: the pre-turn state saved as it first writes, then a new section, a script it
		relies on, an edited script and a new data script"""
		snapshot = save_revert_snapshot(self.page.name, capture_page_state(self.page.name))
		page = frappe.get_doc("Builder Page", self.page.name)
		page.draft_blocks = tree("Old", "New section")
		page.page_data_script = "data.plans = ['new']"
		page.append("client_scripts", {"builder_script": self.script("reveal()")})
		page.save()
		edited = frappe.get_doc("Builder Client Script", self.before)
		edited.script = "show('after')"
		edited.save()
		return snapshot

	def publish_page(self) -> str:
		with hosting_hooks(builder_agent_tools=[]):
			runner = AgentRunner("publish it", model="m", api_key="k", page_id=self.page.name)
		return runner.run_handler(
			runner.registry.get("publish_page"), {"tool_name": "publish_page", "args": {}}
		)

	def revert(self, snapshot: str) -> tuple:
		result = frappe.get_doc("Builder Page", self.page.name).restore_snapshot(snapshot)
		page = frappe.get_doc("Builder Page", self.page.name)
		scripts = [row.builder_script for row in page.client_scripts]
		before = frappe.db.get_value("Builder Client Script", self.before, "script")
		return result, page, scripts, before

	def test_a_turn_bob_published_keeps_its_scripts_and_only_the_draft_goes_back(self):
		self.page.publish()
		snapshot = self.run_turn()
		self.assertEqual(self.publish_page(), f"Published Revert (/revert-{self.tag}).")

		result, page, scripts, before = self.revert(snapshot)

		self.assertIn("New section", page.blocks)
		self.assertNotIn("New section", page.draft_blocks)
		self.assertEqual(len(scripts), 2)
		self.assertEqual(before, "show('after')")
		self.assertEqual(page.page_data_script, "data.plans = ['new']")
		self.assertTrue(any(warning.startswith(KEPT_LIVE) for warning in result["warnings"]))

	def test_a_turn_staged_after_it_keeps_its_scripts_too(self):
		snapshot = self.run_turn()
		frappe.get_doc("Builder Page", self.page.name).publish_to_staging()

		result, page, scripts, before = self.revert(snapshot)

		self.assertIn("New section", page.blocks)
		self.assertEqual(len(scripts), 2)
		self.assertEqual(before, "show('after')")
		self.assertTrue(any(warning.startswith(KEPT_LIVE) for warning in result["warnings"]))

	def test_a_turn_nobody_published_puts_the_scripts_back_with_the_draft(self):
		"""The page was live before the turn, and the turn's work never went there"""
		self.page.publish()
		snapshot = self.run_turn()

		result, page, scripts, before = self.revert(snapshot)

		self.assertNotIn("New section", page.blocks)
		self.assertNotIn("New section", page.draft_blocks)
		self.assertEqual(scripts, [self.before])
		self.assertEqual(before, "show('before')")
		self.assertEqual(page.page_data_script, "data.plans = ['old']")
		self.assertFalse(any(warning.startswith(KEPT_LIVE) for warning in result["warnings"]))


def remove_script_files(name: str) -> None:
	for path in glob.glob(get_files_path(f"page_scripts/{name}-*")):
		os.remove(path)
