from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import activity_summary
from builder.ai.agent.tools.generate import generate_page
from builder.ai.skills import Skills


class TestSkills(FrappeTestCase):
	def test_portfolio_is_registered(self):
		self.assertIn("portfolio", Skills.names())
		self.assertTrue(Skills.get("portfolio").startswith("SKILL: PORTFOLIO"))

	def test_lookup_is_forgiving(self):
		self.assertEqual(Skills.get(" Portfolio "), Skills.PORTFOLIO)
		self.assertEqual(Skills.get("unknown"), "")
		self.assertEqual(Skills.get(""), "")

	def test_generate_page_offers_every_skill(self):
		skill_param = generate_page.parameters["properties"]["skill"]
		self.assertEqual(skill_param["enum"], Skills.names())
		self.assertNotIn("skill", generate_page.parameters["required"])

	def test_timeline_names_the_loaded_skill(self):
		args = {"brief": "a page", "skill": "portfolio"}
		self.assertEqual(
			activity_summary("generate_page", args, done=False), "Building the page (portfolio playbook)"
		)
		self.assertEqual(activity_summary("generate_page", args), "Built the page (portfolio playbook)")
		self.assertEqual(activity_summary("generate_page", {"brief": "a page"}), "Built the page")
