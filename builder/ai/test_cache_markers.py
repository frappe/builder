from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import (
	SYSTEM_CACHE_CONTROL,
	TURN_CACHE_CONTROL,
	AgentRunner,
	marker_position,
)


def msg(role="user", content="x", **extra):
	return {"role": role, "content": content, **extra}


def tool_call_msg():
	return {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]}


class TestCacheMarkers(FrappeTestCase):
	def refresh(self, messages, history_end, prompt):
		runner = AgentRunner("hi", model="m", api_key="k")
		runner.history_end_index = history_end
		runner.prompt_index = prompt
		runner.refresh_cache_markers(messages)

	def test_cross_turn_breakpoints_get_the_long_ttl(self):
		messages = [msg("system"), msg(), msg("assistant"), msg(), msg("assistant"), msg()]

		self.refresh(messages, history_end=2, prompt=3)

		# System and end-of-history survive the between-turn gap; the rest are per-round.
		self.assertEqual(messages[0]["cache_control"], SYSTEM_CACHE_CONTROL)
		self.assertEqual(messages[2]["cache_control"], SYSTEM_CACHE_CONTROL)
		self.assertEqual(messages[3]["cache_control"], TURN_CACHE_CONTROL)
		self.assertEqual(messages[5]["cache_control"], TURN_CACHE_CONTROL)

	def test_marker_never_lands_on_a_content_less_message(self):
		messages = [msg("system"), msg(), tool_call_msg()]

		self.refresh(messages, history_end=0, prompt=1)

		self.assertNotIn("cache_control", messages[2])
		self.assertIn("cache_control", messages[1])

	def test_marker_position_walks_back_to_content(self):
		messages = [msg(), msg("tool", "result"), tool_call_msg()]

		self.assertEqual(marker_position(messages, 2), 1)
		self.assertEqual(marker_position(messages, 1), 1)
