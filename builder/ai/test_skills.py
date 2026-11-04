from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.registry import build_default_registry
from builder.ai.agent.tree import WorkingTree


def offered(skills=None) -> set[str]:
	return {schema["function"]["name"] for schema in build_default_registry().schemas(skills)}


def runner_on(root) -> AgentRunner:
	runner = AgentRunner("hi", model="m", api_key="k", page_id="page-x")
	runner.tree = WorkingTree(root)
	return runner


class TestSkillBoundTools(FrappeTestCase):
	def test_a_skill_bound_tool_is_offered_only_with_its_skill(self):
		self.assertNotIn("connect_form", offered())
		self.assertIn("connect_form", offered({"forms-and-data"}))
		self.assertNotIn("edit_component", offered({"forms-and-data"}))
		self.assertIn("extract_component", offered())

	def test_calling_one_before_its_skill_asks_for_the_skill(self):
		runner = runner_on({"blockId": "root", "children": []})
		tool = runner.registry.get("write_page_data_script")

		out = runner.run_handler(tool, {"tool_name": tool.name, "args": {}})

		self.assertIn("read_skill('forms-and-data')", out)

	def test_a_page_with_a_component_brings_the_components_skill(self):
		instance = {
			"blockId": "nav123456",
			"element": "div",
			"extendedFromComponent": "c-missing",
			"children": [],
		}
		runner = runner_on({"blockId": "root", "element": "div", "children": [instance]})

		out = runner.build_initial_page_context()

		self.assertIn("components skill in full", out)
		self.assertIn("components", runner.attached_skills)
