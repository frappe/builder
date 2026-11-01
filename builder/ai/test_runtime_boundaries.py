import unittest
from types import SimpleNamespace
from unittest.mock import patch

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.registry import ToolRegistry, build_default_registry
from builder.ai.agent.tools.toolsets import load_tools
from builder.ai.agent.tree import WorkingTree


def streamed_call(arguments, reason="tool_calls"):
	call = SimpleNamespace(
		index=0, id="call-1", function=SimpleNamespace(name="update_block", arguments=arguments)
	)
	delta = SimpleNamespace(content=None, tool_calls=[call])
	return [SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason, delta=delta)], usage=None)]


class TestRuntimeBoundaries(unittest.TestCase):
	def runner(self):
		return AgentRunner("edit", "test/model", "test-only", registry=ToolRegistry())

	def test_truncated_response_never_produces_executable_operations(self):
		runner = self.runner()
		with (
			patch(
				"builder.ai.agent.loop.llm.complete_with_tools",
				return_value=streamed_call('{"block_id":"hero","inner_text":"partial"', "length"),
			),
			patch.object(runner, "emit"),
		):
			with self.assertRaises(ValueError):
				runner.stream_tool_round([])
		self.assertEqual(runner.finish_reasons, ["length"])

	def test_invalid_json_is_not_repaired_into_an_edit(self):
		runner = self.runner()
		with (
			patch(
				"builder.ai.agent.loop.llm.complete_with_tools",
				return_value=streamed_call('{"block_id":"hero",}'),
			),
			patch.object(runner, "emit"),
		):
			with self.assertRaises(ValueError):
				runner.stream_tool_round([])

	def test_valid_complete_call_is_preserved(self):
		runner = self.runner()
		with (
			patch(
				"builder.ai.agent.loop.llm.complete_with_tools",
				return_value=streamed_call('{"block_id":"hero","inner_text":"Hello"}'),
			),
			patch.object(runner, "emit"),
		):
			operations, _, calls = runner.stream_tool_round([])
		self.assertEqual(operations[0]["args"]["inner_text"], "Hello")
		self.assertEqual(calls[0]["id"], "call-1")

	def test_partial_bulk_edit_emits_only_accepted_operations(self):
		runner = self.runner()
		runner.tree = WorkingTree(
			{
				"blockId": "root",
				"element": "div",
				"children": [{"blockId": "title", "element": "h1", "innerHTML": "Old"}],
			}
		)
		op = {"tool_name": "update_blocks", "args": {"block_ids": ["title", "missing"], "inner_text": "New"}}
		with patch.object(runner, "emit") as emit:
			_, applied = runner.apply_client_ops([op])
		self.assertEqual(len(applied), 1)
		self.assertEqual(applied[0]["args"]["block_id"], "title")
		self.assertEqual(emit.call_args.kwargs["operations"], applied)

	def test_tool_groups_are_lazy_and_remain_available(self):
		registry = build_default_registry()

		def names():
			return {schema["function"]["name"] for schema in registry.schemas()}

		self.assertNotIn("generate_page", names())
		load_tools(SimpleNamespace(registry=registry), {"groups": ["design", "data"]})
		self.assertIn("generate_page", names())
		self.assertIn("connect_form", names())
		self.assertNotIn("write_plugin", names())

	def test_compaction_keeps_tool_call_result_pairs(self):
		runner = self.runner()
		runner.prompt_index = 0
		messages = [{"role": "user", "content": "edit"}]
		for i in range(7):
			messages.extend(
				[
					{"role": "assistant", "tool_calls": [{"id": str(i)}]},
					{"role": "tool", "tool_call_id": str(i), "content": "result" * 5000},
				]
			)
		runner.compact_tool_history(messages)
		self.assertEqual(len(messages), 8)
		self.assertEqual(messages[1]["role"], "user")
		for i in range(2, len(messages), 2):
			self.assertEqual(messages[i]["tool_calls"][0]["id"], messages[i + 1]["tool_call_id"])
		self.assertLess(len(messages[1]["content"]), 4200)

	def test_result_budget_is_explicit(self):
		result = AgentRunner.bounded_result("x" * 50000)
		self.assertLess(len(result), 16100)
		self.assertIn("truncated", result)
