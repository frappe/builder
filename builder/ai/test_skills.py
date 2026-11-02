import json
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from builder.ai import llm
from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.tools.plugins import run_write_plugin, write_plugin_tool
from builder.ai.agent.tools.query import MAX_PAGE_READS_PER_TURN, run_read_page
from builder.ai.agent.tools.skills import run_read_skill
from builder.ai.agent.tree import WorkingTree
from builder.ai.skills import Skills


class TestSkillContext(TestCase):
	def runner(self, prompt="Add an editor panel", empty=False, selected=()):
		runner = AgentRunner(prompt, model="m", api_key="k", page_id="page-test", selected_block_ids=selected)
		runner.tree = WorkingTree(
			{
				"blockId": "root",
				"element": "div",
				"children": []
				if empty
				else [
					{
						"blockId": "headline",
						"element": "h1",
						"innerHTML": "Selected headline",
						"baseStyles": {"color": "red"},
					},
					{"blockId": "footer", "element": "p", "innerHTML": "Unrelated page content"},
				],
			}
		)
		return runner

	def messages(self, runner, history=()):
		with (
			patch.object(runner, "build_open_page_context", return_value="Open page: page-test"),
			patch.object(runner, "build_memory_context", return_value="Saved memory: keep it concise"),
			patch(
				"builder.ai.agent.loop.AISession.build_context_messages_from_id", return_value=list(history)
			),
			patch("builder.ai.agent.loop.ModelRegistry.supports_vision", return_value=False),
		):
			return runner.build_messages()

	def next_round(self, runner):
		with patch.object(runner, "stream_tool_round", return_value=([], "", [])):
			runner.call_tool_llm([])

	def test_initial_context_is_lazy_regardless_of_wording_or_history(self):
		prompts = (
			"Create a plugin for auditing images",
			"Add a panel to the editor listing images without alt text",
			"A toolbar action to copy the page as markdown",
			"Make its button smaller",
			"Build the plugin and make the hero red",
			"Translate the whole page",
		)
		for empty in (True, False):
			for prompt in prompts:
				with self.subTest(empty=empty, prompt=prompt):
					runner = self.runner(prompt, empty=empty)
					messages = self.messages(runner, [{"role": "assistant", "content": "Added the panel."}])
					context = messages[2]["content"]
					self.assertIn("read_page('page-test')", context)
					self.assertIn("Saved memory", context)
					self.assertNotIn("Unrelated page content", context)
					self.assertNotIn(Skills.read("new-page"), context)
					self.assertNotIn(Skills.read("editor-plugin"), context)
					self.assertFalse(runner.attached_skills)

	def test_selected_blocks_keep_styles_and_scope_without_unrelated_page_content(self):
		runner = self.runner("Make this red and add an editor action", selected=["headline", "missing"])
		messages = self.messages(runner)
		context, prompt = messages[1]["content"], messages[-1]["content"]
		self.assertIn("Selected headline", context)
		self.assertIn("red", context)
		self.assertNotIn("Unrelated page content", context)
		self.assertIn("ATTACHED BLOCKS", prompt)
		self.assertIn("headline (<h1>)", prompt)

	def test_fixed_system_and_tool_prefix_survives_reads_rounds_and_new_turns(self):
		first = self.runner()
		second = self.runner("Continue", empty=True, selected=["root"])
		original_schemas = json.dumps(first.registry.schemas())
		initial = self.messages(first)
		run_read_skill(first, {"name": "editor-plugin"})
		self.next_round(first)
		continued = self.messages(second, [{"role": "assistant", "content": "Added the panel."}])
		self.assertEqual(initial[0], continued[0])
		self.assertEqual(original_schemas, json.dumps(first.registry.schemas()))
		self.assertEqual(original_schemas, json.dumps(second.registry.schemas()))
		for model in ("openrouter/anthropic/claude-sonnet-5.5", "openai/gpt-test"):
			messages = deepcopy(initial)
			first.refresh_cache_markers(messages)
			llm.patch_messages_for_provider(model, messages)
			self.assertEqual(
				messages[0]["content"][0]["text"] if "claude-" in model else messages[0]["content"],
				initial[0]["content"],
			)

	def test_open_page_read_uses_current_tree_even_after_reference_budget_is_spent(self):
		runner = self.runner()
		runner.page_read_count = MAX_PAGE_READS_PER_TURN
		runner.tree.root["children"][0]["innerHTML"] = "Edited this round"
		with (
			patch("builder.ai.agent.tools.query.resolve_page_reference", return_value=(runner.page_id, "")),
			patch("builder.ai.agent.tools.query.render_scripts", return_value="Attached CSS"),
		):
			context = run_read_page(runner, {"page_id": runner.page_id})
		self.assertIn("Edited this round", context)
		self.assertIn("ref: headline", context)
		self.assertIn("Unrelated page content", context)
		self.assertIn("Attached CSS", context)
		self.assertNotIn("READ-ONLY", context)

	def test_empty_page_read_supplies_build_skill_once(self):
		runner = self.runner(empty=True)
		with (
			patch("builder.ai.agent.tools.query.resolve_page_reference", return_value=(runner.page_id, "")),
			patch("builder.ai.agent.tools.query.render_scripts", return_value=""),
		):
			context = run_read_page(runner, {"page_id": runner.page_id})
			self.assertIn(Skills.read("new-page"), context)
			self.assertNotIn(Skills.read("new-page"), run_read_page(runner, {"page_id": runner.page_id}))
		self.assertIn("already in your context", run_read_skill(runner, {"name": "new-page"}))

	def test_skill_read_is_deduplicated_but_a_new_turn_must_read_again(self):
		runner = self.runner()
		guide = run_read_skill(runner, {"name": "editor-plugin"})
		self.assertEqual(guide, Skills.read("editor-plugin"))
		self.assertIn("already in your context", run_read_skill(runner, {"name": "editor-plugin"}))
		self.assertEqual(guide, run_read_skill(self.runner("Continue"), {"name": "editor-plugin"}))
		self.assertTrue(run_read_skill(runner, {"name": "../prompts"}).startswith("FAILED"))

	def test_plugin_write_requires_guide_in_a_previous_model_round(self):
		runner = self.runner()
		doc = SimpleNamespace(plugin="bob/audit", enabled=True)
		args = {
			"name": "audit",
			"label": "Audit",
			"description": "Audit images.",
			"code": "export default {}",
		}
		with (
			patch("builder.ai.agent.tools.plugins.is_plugin_manager", return_value=True),
			patch("builder.ai.agent.tools.plugins.bob.syntax_error", return_value=None),
			patch("builder.ai.agent.tools.plugins.bob.save_plugin", return_value=doc) as save,
			patch("builder.ai.agent.tools.plugins.load_in_editor", return_value="Running") as load,
		):
			self.assertTrue(run_write_plugin(runner, args).startswith("FAILED"))
			run_read_skill(runner, {"name": "editor-plugin"})
			self.assertTrue(run_write_plugin(runner, args).startswith("FAILED"))
			save.assert_not_called()
			self.next_round(runner)
			self.assertEqual(run_write_plugin(runner, args), "Running")
			save.assert_called_once_with("audit", "Audit", "Audit images.", "export default {}", None)
			load.assert_called_once_with(runner, doc)
			self.assertTrue(run_write_plugin(self.runner("Change the panel"), args).startswith("FAILED"))
			self.assertEqual(save.call_count, 1)

	def test_generation_also_waits_for_its_guide(self):
		runner = self.runner(empty=True)
		tool = Mock(generator=Mock(return_value=[]))
		op = {"tool_name": "generate_page", "args": {"brief": "Build it"}}
		self.assertIn("read_skill('new-page')", runner.run_generation_step(tool, op)[0])
		run_read_skill(runner, {"name": "new-page"})
		self.assertIn("read_skill('new-page')", runner.run_generation_step(tool, op)[0])
		tool.generator.assert_not_called()
		self.next_round(runner)
		with (
			patch.object(runner, "begin_activity"),
			patch.object(runner, "end_activity"),
			patch.object(runner, "ensure_revert_snapshot"),
		):
			runner.run_generation_step(tool, op)
		tool.generator.assert_called_once()

	def test_skill_read_does_not_count_as_a_mutation(self):
		runner = self.runner()
		with (
			patch.object(runner, "begin_activity"),
			patch.object(runner, "end_activity"),
			patch.object(runner, "drain_queued_ops"),
			patch.object(runner, "run_handler", return_value=Skills.read("editor-plugin")),
		):
			runner.run_op({"tool_name": "read_skill", "args": {"name": "editor-plugin"}}, {})
		self.assertEqual(runner.server_mutations, 0)

	def test_plugin_schema_keeps_behavior_but_moves_authoring_details_to_skill(self):
		self.assertIn("installs the plugin for everyone", write_plugin_tool.description)
		self.assertIn("WHOLE file", write_plugin_tool.description)
		self.assertIn("read_skill('editor-plugin')", write_plugin_tool.description)
		for detail in (
			"runtime-only",
			"propertySections",
			"text-ink-gray-9",
			"minHeight",
			"activePageScripts",
		):
			self.assertIn(detail, Skills.read("editor-plugin"))
			self.assertNotIn(detail, write_plugin_tool.description)
