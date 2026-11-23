"""Bob publishes as the editor's Publish button does (publish_page): through the page's own save, so what a
hosting app checks on save when a person publishes holds for him too. frappe.page's own site refuses, in its
validate hook, a landing page that would render template syntax or sit outside the landing's route; a publish
that wrote `published` with frappe.db.set_value would go past it. And he leaves alone a page another chat's
turn is building, as his other writes to a page do."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import locks
from builder.ai.agent.loop import AgentRunner
from builder.ai.test_page_changes import heading, make_page
from builder.builder.tests.hosting_hooks import hosting_hooks


def refuse_on_save(doc, method=None):
	frappe.throw("Not allowed on this host")


def host_save_hooks(*validate):
	"""Only these validate hooks on Builder Page, whatever apps the site has"""
	hooks = {"Builder Page": {"validate": [f"{__name__}.{hook.__name__}" for hook in validate]}}
	return patch.object(frappe.local, "doc_events_hooks", hooks, create=True)


class TestPublishPage(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.route = f"pub-{frappe.generate_hash(length=6)}"
		self.page_id = make_page("Launch", self.route, [heading("pubhead", "Hi")])
		with hosting_hooks(builder_agent_tools=[]):
			self.runner = AgentRunner("publish it", model="m", api_key="k", page_id=self.page_id)

	def publish(self, *pages: str) -> str:
		op = {"tool_name": "publish_page", "args": {"pages": list(pages)} if pages else {}}
		self.assertEqual(self.runner.op_kind(op), "server")
		return self.runner.run_handler(self.runner.registry.get("publish_page"), op)

	def state(self) -> tuple:
		return frappe.db.get_value("Builder Page", self.page_id, ["published", "blocks", "draft_blocks"])

	def test_a_publish_the_host_refuses_on_save_leaves_the_page_a_draft(self):
		with host_save_hooks(refuse_on_save):
			out = self.publish()

		self.assertTrue(out.startswith("FAILED"), out)
		self.assertIn("Not allowed on this host", out)
		published, _blocks, draft = self.state()
		self.assertFalse(published)
		self.assertIn("pubhead", draft)

	def test_a_publish_the_host_allows_goes_live_as_the_publish_button_makes_it(self):
		with host_save_hooks():
			out = self.publish()

		self.assertEqual(out, f"Published Launch (/{self.route}).")
		published, blocks, draft = self.state()
		self.assertTrue(published)
		self.assertIn("pubhead", blocks)
		self.assertFalse(draft)

	def test_a_page_another_chat_is_building_stays_as_it_was(self):
		"""That chat's turn saves its draft after every batch, so the draft under its lock is half built"""
		other = make_page("Pricing", f"{self.route}-pricing", [heading("halfbuilt", "Half built")])
		key = locks.page_key(other)
		token = locks.acquire(key, 60)
		self.addCleanup(locks.release, key, token)

		with host_save_hooks():
			out = self.publish(other)

		self.assertEqual(
			out,
			f"NOT PUBLISHED: Pricing (/{self.route}-pricing) is being edited by another AI task right now. "
			"Tell the user to publish it once that finishes.",
		)
		published, blocks, draft = frappe.db.get_value(
			"Builder Page", other, ["published", "blocks", "draft_blocks"]
		)
		self.assertFalse(published)
		self.assertNotIn("halfbuilt", blocks or "")
		self.assertIn("halfbuilt", draft)
		self.assertTrue(locks.held(key))

	def test_a_page_no_task_holds_goes_live_and_its_lock_is_let_go(self):
		other = make_page("Pricing", f"{self.route}-pricing", [heading("pricehead", "Plans")])

		with host_save_hooks():
			out = self.publish(other)

		self.assertEqual(out, f"Published Pricing (/{self.route}-pricing).")
		self.assertTrue(frappe.db.get_value("Builder Page", other, "published"))
		self.assertFalse(locks.held(locks.page_key(other)))

	def test_the_turns_own_page_goes_live_under_the_lock_the_turn_holds(self):
		self.assertEqual(self.runner.load_page(self.page_id), "")
		self.addCleanup(lambda: [locks.release(*held) for held in self.runner.held_locks])

		with host_save_hooks():
			out = self.publish()

		self.assertEqual(out, f"Published Launch (/{self.route}).")
		self.assertTrue(self.state()[0])
		self.assertTrue(locks.held(locks.page_key(self.page_id)))
