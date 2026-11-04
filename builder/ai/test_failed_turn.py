import time
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner


class TestFailedTurn(FrappeTestCase):
	def fail(self, runner, *args, **kwargs):
		with (
			patch("builder.ai.agent.loop.AISession.try_append_message") as append,
			patch.object(runner, "emit") as emit,
		):
			runner.fail_turn(*args, **kwargs)
		emit.assert_called_once()
		return append.call_args.kwargs["metadata"]

	def test_keeps_the_error_trace_steps_and_revert(self):
		runner = AgentRunner("hi", model="m", api_key="k")
		runner.trace = [{"round": 0, "tools": [{"name": "read_block", "args": "{}"}], "text": ""}]
		runner.steps = [{"id": 1, "kind": "tool", "tool": "read_block", "status": "done"}]
		runner.revert_snapshot = "snap-1"

		metadata = self.fail(
			runner,
			"Something went wrong.",
			error=TimeoutError("late"),
			started=time.monotonic(),
			error_log="log-1",
		)

		self.assertEqual(metadata["status"], "error")
		self.assertEqual(metadata["debug"]["stopReason"], "error")
		self.assertEqual(metadata["debug"]["error"], "TimeoutError")
		self.assertEqual(metadata["debug"]["errorLog"], "log-1")
		self.assertEqual(metadata["debug"]["rounds"], 1)
		self.assertEqual(metadata["revertSnapshot"], "snap-1")
		self.assertEqual(metadata["steps"], runner.steps)

	def test_a_refusal_before_any_work_stays_bare(self):
		runner = AgentRunner("hi", model="m", api_key="k")

		self.assertEqual(self.fail(runner, "Another AI request is still working."), {"status": "error"})

	def test_a_turn_that_raises_records_its_error_log(self):
		runner = AgentRunner("hi", model="m", api_key="k")
		with (
			patch.object(runner, "build_messages", return_value=[]),
			patch.object(runner, "refresh_cache_markers", side_effect=TimeoutError("late")),
			patch.object(runner, "fail_turn") as fail,
		):
			runner.run_turn(time.monotonic())

		self.assertIsInstance(fail.call_args.kwargs["error"], TimeoutError)
		self.assertTrue(fail.call_args.kwargs["error_log"])
