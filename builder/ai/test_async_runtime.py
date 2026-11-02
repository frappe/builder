import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from builder.ai.runtime import RunWorkflow, codex_chunks, model_batches
from builder.ai.workflow import ModelRequest, consume_stream, drive_sync


class TestWorkflow(unittest.TestCase):
	def test_parallel_reads_never_cross_a_write_or_terminal_boundary(self):
		from builder.ai.agent.registry import build_default_registry
		from builder.ai.scheduling import read_prefix

		registry = build_default_registry()
		read = {"tool_name": "get_document", "args": {"doctype": "Builder Page", "name": "fixture"}}
		for boundary in ("update_block", "present_ui", "research"):
			ops = [read, read, {"tool_name": boundary, "args": {}}, read]
			self.assertEqual(read_prefix(ops, registry), [read, read])
			self.assertEqual(read_prefix(ops[1:], registry), [])

	def test_sync_driver_preserves_batches_and_return_value(self):
		seen = []
		request = ModelRequest("fixture", [], {})

		def workflow():
			yield from consume_stream(request, seen.append)
			return "complete"

		with patch.object(ModelRequest, "synchronous", return_value=iter([1, 2])):
			self.assertEqual(drive_sync(workflow()), "complete")
		self.assertEqual(seen, [1, 2])


class TestAsyncTransport(unittest.IsolatedAsyncioTestCase):
	async def test_startup_cancellation_retires_claimed_run(self):
		class Context:
			async def call(self, callback, *args, **kwargs):
				if callback == run.start:
					run.claimed = True
					raise asyncio.CancelledError()
				return callback(*args)

		run = RunWorkflow(Context(), "starting")
		with patch("builder.ai.runs.AIRun.finish") as finish:
			with self.assertRaises(asyncio.CancelledError):
				await run.run()
		finish.assert_called_once()
		self.assertEqual(finish.call_args.args[:2], ("starting", "cancelled"))

	async def test_codex_401_refreshes_once_before_retrying(self):
		import httpx

		responses = [
			httpx.Response(401, text="Expired"),
			httpx.Response(
				200,
				text='data: {"type":"response.output_text.delta","delta":"Ready"}\n\ndata: {"type":"response.completed","response":{}}\n\n',
			),
		]
		transport = httpx.MockTransport(lambda request: responses.pop(0))
		client = httpx.AsyncClient(transport=transport)
		refresh = AsyncMock()
		request = ModelRequest(
			"fixture",
			[],
			{},
			prepared={"url": "https://example.test/responses", "headers": {}, "payload": {}},
			refresh_auth=refresh,
		)
		with patch("httpx.AsyncClient", return_value=client):
			chunks = [chunk async for chunk in codex_chunks(request)]
		self.assertEqual(refresh.await_count, 2)
		self.assertTrue(refresh.call_args.kwargs["force"])
		self.assertIn("Ready", "".join(chunk.choices[0].delta.content or "" for chunk in chunks))
		self.assertFalse(responses)

	async def test_shutdown_closes_suspended_workflow(self):
		from builder.ai.agent.loop import CancelledError

		closed = []

		def workflow():
			try:
				yield ModelRequest("fixture", [], {})
			except CancelledError:
				closed.append(True)

		run = RunWorkflow(Mock(), "running")
		run.workflow = workflow()
		next(run.workflow)
		run.cancel_workflow()
		self.assertEqual(closed, [True])

	async def test_silent_provider_does_not_hold_other_streams(self):
		started, release = asyncio.Event(), asyncio.Event()
		closed = []

		async def chunks(request):
			try:
				if request.model == "slow":
					started.set()
					await release.wait()
				yield request.model
			finally:
				closed.append(request.model)

		with patch("builder.ai.runtime.model_chunks", chunks):
			slow = model_batches(ModelRequest("slow", [], {}))
			pending = asyncio.create_task(anext(slow))
			await asyncio.wait_for(started.wait(), 1)
			fast = model_batches(ModelRequest("fast", [], {}))
			self.assertEqual(await asyncio.wait_for(anext(fast), 1), ["fast"])
			self.assertFalse(pending.done())
			release.set()
			self.assertEqual(await pending, ["slow"])
			await fast.aclose()
			await slow.aclose()
		self.assertCountEqual(closed, ["slow", "fast"])

	async def test_cancellation_closes_silent_network_wait(self):
		closed = asyncio.Event()

		async def network():
			try:
				await asyncio.Event().wait()
			finally:
				closed.set()

		class Context:
			async def call(self, *args, **kwargs):
				raise ValueError("cancel requested")

		run = RunWorkflow(Context(), "fixture")
		with self.assertRaisesRegex(ValueError, "cancel requested"):
			await asyncio.wait_for(run.waiting(network()), 2)
		self.assertTrue(closed.is_set())

	async def test_partial_batch_flushes_before_next_token(self):
		release = asyncio.Event()

		async def chunks(request):
			yield "first"
			await release.wait()
			yield "second"

		with patch("builder.ai.runtime.model_chunks", chunks):
			stream = model_batches(ModelRequest("fixture", [], {}))
			self.assertEqual(await asyncio.wait_for(anext(stream), 0.5), ["first"])
			release.set()
			self.assertEqual(await anext(stream), ["second"])
			await stream.aclose()
