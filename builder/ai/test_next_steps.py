import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.tools.conversation import sanitize_next_steps
from builder.ai.session import AISession


class TestNextSteps(FrappeTestCase):
	def test_suggestions_are_bounded_and_invalid_or_duplicate_options_are_dropped(self):
		first = {"label": "  Add\nvisit hours ", "prompt": " Ask me for the studio's real opening hours. "}
		second = {"label": "Choose a photo", "prompt": "Show photos that fit this ceramics studio."}
		third = {"label": "Check booking", "prompt": "Check the existing booking link."}
		self.assertEqual(
			sanitize_next_steps(
				[
					None,
					{"label": 123, "prompt": "bad"},
					{"label": " ", "prompt": "bad"},
					{"label": "Too long", "prompt": "x" * 601},
					first,
					{"label": "ADD VISIT HOURS", "prompt": "Duplicate label"},
					{**second, "prompt": first["prompt"].strip()},
					second,
					third,
					{"label": "Extra", "prompt": "Fourth suggestion"},
				]
			),
			[{"label": "Add visit hours", "prompt": first["prompt"].strip()}, second, third],
		)
		self.assertEqual(sanitize_next_steps({"label": "Not an array"}), [])

	def test_one_model_response_persists_reply_and_suggestions_and_emits_completion(self):
		steps = [{"label": "Add visit hours", "prompt": "Ask me for the studio's real opening hours."}]
		args = {"message": "The studio introduction is ready.", "next_steps": steps}
		call = SimpleNamespace(
			index=0,
			id="finish-1",
			function=SimpleNamespace(name="finish_response", arguments=json.dumps(args)),
		)
		chunk = SimpleNamespace(
			choices=[
				SimpleNamespace(
					finish_reason="tool_calls", delta=SimpleNamespace(content=None, tool_calls=[call])
				)
			],
			usage=None,
		)
		session = AISession.create({"title": "Next-step regression"})
		runner = AgentRunner("Help with my studio", "test/model", "test-only", session_id=session.name)
		with (
			patch("builder.ai.agent.loop.llm.complete_with_tools", return_value=[chunk]) as model,
			patch.object(runner, "checkpoint"),
			patch.object(runner, "is_cancelled", return_value=False),
			patch("frappe.publish_realtime") as publish,
		):
			runner.run_turn(runner.started)
		model.assert_called_once()
		self.assertIn("finish_response", {tool["function"]["name"] for tool in model.call_args.args[2]})
		self.assertEqual(runner.terminal_status, "complete")
		message = AISession.get(session.name).get_messages()[-1]
		self.assertEqual(message["content"], args["message"])
		self.assertEqual(message["metadata"]["nextSteps"], steps)
		self.assertEqual(runner.turn_metadata()["nextSteps"], steps)
		completions = [c.args[1] for c in publish.call_args_list if c.args[0].startswith("ai_chat_complete")]
		self.assertEqual(len(completions), 1)
		self.assertEqual(completions[0]["next_steps"], steps)

	def test_plain_reply_remains_usable_without_invented_suggestions(self):
		session = AISession.create({"title": "Plain reply regression"})
		runner = AgentRunner("Thanks", "test/model", "test-only", session_id=session.name)
		with patch("frappe.publish_realtime"):
			runner.finish_turn("You're welcome.", runner.started)
		message = AISession.get(session.name).get_messages()[-1]
		self.assertEqual(message["content"], "You're welcome.")
		self.assertEqual(message["metadata"]["nextSteps"], [])
