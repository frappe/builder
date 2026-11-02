"""Async provider waits with short, isolated Frappe execution slices.

Run with: python -m builder.ai.runtime --site SITE --sites-path /bench/sites
The daemon owns orchestration. Ordinary tools use a bounded thread pool; no
Frappe/RQ worker or database connection is held while a model streams.
"""

import argparse
import asyncio
import inspect
import json
import logging
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial

import frappe

from builder.ai.scheduling import ReadBatch, perform_read
from builder.ai.workflow import MORE, Delay, ModelRequest

logger = logging.getLogger(__name__)


async def codex_chunks(request):
	import httpx

	from builder.ai import codex

	prepared = request.prepared
	async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
		await request.refresh_auth(request, client)
		for attempt in range(2):
			async with client.stream(
				"POST", prepared["url"], headers=prepared["headers"], json=prepared["payload"]
			) as response:
				if response.status_code == 401 and attempt == 0:
					await response.aread()
					await request.refresh_auth(request, client, force=True)
					continue
				if response.status_code >= 400:
					await response.aread()
					raise codex.http_error(response)
				assembler, data = codex.ChunkAssembler(), []
				async for line in response.aiter_lines():
					if line.startswith("data:"):
						data.append(line[5:].strip())
					elif not line and data:
						for chunk in assembler.feed(codex.parse_event("\n".join(data))):
							yield chunk
						data = []
						if assembler.finished:
							return
				if data:
					for chunk in assembler.feed(codex.parse_event("\n".join(data))):
						yield chunk
				return


async def model_chunks(request):
	if request.prepared["transport"] == "codex":
		async for chunk in codex_chunks(request):
			yield chunk
		return
	import litellm

	response = await litellm.acompletion(**request.prepared["payload"])
	if not request.stream:
		yield response
		return
	try:
		async for chunk in response:
			yield chunk
	finally:
		if close := getattr(response, "aclose", None):
			await close()


async def model_batches(request):
	"""Batch deltas without waiting for a silent provider to produce the next token."""
	chunks = model_chunks(request).__aiter__()
	pending, batch = None, []
	try:
		while True:
			if pending is None:
				pending = asyncio.create_task(chunks.__anext__())
			done, _ = await asyncio.wait({pending}, timeout=0.1 if batch else None)
			if not done:
				yield batch
				batch = []
				continue
			try:
				chunk = pending.result()
			except StopAsyncIteration:
				if batch:
					yield batch
				return
			pending = None
			batch.append(chunk)
			if len(batch) >= 32 or not request.stream:
				yield batch
				batch = []
	finally:
		if pending and not pending.done():
			pending.cancel()
			with suppress(asyncio.CancelledError):
				await pending
		await chunks.aclose()


class SiteContext:
	def __init__(self, site, sites_path, executor):
		self.site, self.sites_path, self.executor = site, sites_path, executor
		self.auth_locks = {}

	def invoke(self, callback, user, *args):
		frappe.init(site=self.site, sites_path=self.sites_path)
		try:
			frappe.connect()
			frappe.set_user(user or "Administrator")
			result = callback(*args)
			frappe.db.commit()
			return result
		except BaseException:
			if getattr(frappe.local, "db", None):
				frappe.db.rollback()
			raise
		finally:
			frappe.destroy()

	async def call(self, callback, *args, user=None):
		pending = asyncio.get_running_loop().run_in_executor(
			self.executor, partial(self.invoke, callback, user, *args)
		)
		try:
			return await asyncio.shield(pending)
		except asyncio.CancelledError:
			# A running thread cannot be cancelled. Let its slice settle before closing
			# or throwing into the generator; advancing it concurrently corrupts state.
			with suppress(Exception):
				await pending
			raise


class RunWorkflow:
	def __init__(self, context, run_id):
		self.context, self.run_id = context, run_id
		self.user = None
		self.runner = self.workflow = None
		self.claimed = False
		self.started = time.monotonic()

	def start(self):
		from builder.ai import llm
		from builder.ai.agent.loop import AgentRunner
		from builder.ai.runs import AIRun
		from builder.ai.session import AISession

		if not AIRun.claim(self.run_id):
			return False
		self.claimed = True
		doc = frappe.get_doc(AIRun.DOCTYPE, self.run_id)
		self.user = doc.run_user
		frappe.set_user(self.user)
		try:
			frappe.get_doc("Builder Page", doc.page).check_permission("write")
			AISession.get(doc.session, page_id=doc.page)
			payload = json.loads(doc.payload_json)
			payload.pop("api_key", None)
			self.runner = AgentRunner(api_key=llm.resolve_api_key(doc.model), **payload)
			self.workflow = self.runner.iter_run()
			return True
		except Exception:
			metadata = {
				"status": "error",
				"runId": doc.name,
				"reason": "Check your page access and model connection, then retry.",
			}
			AIRun.finish(doc.name, "failed", metadata)
			AISession.try_append_message(
				doc.session, "assistant", metadata["reason"], message_type="status", metadata=metadata
			)
			frappe.db.commit()
			raise

	def advance(self, value=None, error=None):
		while True:
			try:
				command = self.workflow.throw(error) if error else self.workflow.send(value)
			except StopIteration:
				return True, None
			error = None
			try:
				if isinstance(command, ModelRequest):
					command.prepare(asynchronous=True)
					command.refresh_auth = self.refresh_auth
				return False, command
			except Exception as exc:
				error = exc

	async def refresh_auth(self, request, client, force=False):
		from builder.ai import codex

		prepared = request.prepared
		provider = prepared["provider"]
		async with self.context.auth_locks.setdefault(provider, asyncio.Lock()):
			credential = await self.context.call(codex.stored_credential, provider, user=self.user)
			stale = (
				not credential.get("access")
				or credential.get("expires", 0) - codex.REFRESH_SLACK_MS < time.time() * 1000
			)
			if stale or (force and credential.get("access") == prepared["credential"].get("access")):
				response = await client.post(
					codex.TOKEN_URL,
					data={
						"grant_type": "refresh_token",
						"client_id": codex.CLIENT_ID,
						"refresh_token": credential["refresh"],
					},
				)
				if response.status_code >= 400:
					raise codex.CodexCredentialError(
						"The ChatGPT sign-in has expired. Sign in again from AI settings."
					)
				data = response.json()
				updated = {
					**credential,
					"access": data["access_token"],
					"refresh": data.get("refresh_token") or credential["refresh"],
					"expires": int(time.time() * 1000) + int(data.get("expires_in") or 3600) * 1000,
				}
				credential = await self.context.call(
					save_refreshed_auth, provider, credential, updated, user=self.user
				)
			if not credential.get("account_id"):
				raise codex.CodexCredentialError(
					"The ChatGPT sign-in has no account ID. Sign in again from AI settings."
				)
			prepared.update(
				credential=credential,
				headers=codex.request_headers(credential["access"], credential["account_id"]),
			)

	def cancel_workflow(self):
		from builder.ai.agent.loop import CancelledError
		from builder.ai.runs import AIRun
		from builder.ai.session import AISession

		if self.workflow and inspect.getgeneratorstate(self.workflow) == inspect.GEN_SUSPENDED:
			self.advance(None, CancelledError())
		elif self.claimed:
			metadata = {
				"status": "cancelled",
				"runId": self.run_id,
				"reason": "The service stopped before this turn began. Retry to continue.",
			}
			if AIRun.finish(self.run_id, "cancelled", metadata) and self.runner:
				AISession.try_append_message(
					self.runner.session_id,
					"assistant",
					metadata["reason"],
					message_type="status",
					metadata=metadata,
				)

	def heartbeat(self):
		from builder.ai.agent.loop import CancelledError
		from builder.ai.runs import AIRun

		doc = frappe.get_doc(AIRun.DOCTYPE, self.run_id, for_update=True)
		if doc.cancel_requested or doc.status != "running":
			raise CancelledError()
		if time.monotonic() - self.started > 600:
			raise TimeoutError("The run reached its ten-minute execution limit")
		frappe.db.set_value(
			AIRun.DOCTYPE, self.run_id, "heartbeat_on", frappe.utils.now_datetime(), update_modified=False
		)

	async def waiting(self, awaitable):
		pending = asyncio.ensure_future(awaitable)
		try:
			while True:
				done, _ = await asyncio.wait({pending}, timeout=1)
				await self.context.call(self.heartbeat, user=self.user)
				if done:
					return pending.result()
		finally:
			if not pending.done():
				pending.cancel()
				with suppress(asyncio.CancelledError):
					await pending

	async def run(self):
		stream, value, error = None, None, None
		try:
			if not await self.context.call(self.start):
				return
			while True:
				done, command = await self.context.call(self.advance, value, error, user=self.user)
				if done:
					return
				value, error = None, None
				try:
					if isinstance(command, Delay):
						await self.waiting(asyncio.sleep(command.seconds))
					elif isinstance(command, ReadBatch):
						value = await self.waiting(
							asyncio.gather(
								*(
									self.context.call(perform_read, command, op, user=self.user)
									for op in command.operations
								)
							)
						)
					elif isinstance(command, ModelRequest):
						if stream:
							await stream.aclose()
						stream = model_batches(command).__aiter__()
						value = await self.waiting(anext(stream, None))
						if not command.stream:
							value = value[0] if value else None
					elif command is MORE:
						value = await self.waiting(anext(stream, None))
					else:
						raise TypeError("Unknown workflow command")
				except Exception as exc:
					error = exc
		except asyncio.CancelledError:
			await self.context.call(self.cancel_workflow, user=self.user)
			raise
		finally:
			if stream:
				await stream.aclose()
			if self.workflow:
				await self.context.call(self.workflow.close, user=self.user)


def save_refreshed_auth(provider, previous, updated):
	from builder.ai import codex

	frappe.db.get_value("Builder AI Provider", provider, "name", for_update=True)
	current = codex.stored_credential(provider)
	if current != previous:
		return current
	codex.save_credential(provider, updated)
	return updated


def queued_runs(limit):
	from builder.ai.runs import AIRun

	if frappe.conf.get("builder_ai_runtime") != "async":
		raise RuntimeError("Set builder_ai_runtime=async before starting the daemon")
	return frappe.get_all(
		AIRun.DOCTYPE,
		filters={"status": "queued", "payload_json": ["is", "set"]},
		pluck="name",
		order_by="creation asc",
		limit=limit,
	)


async def serve(site, sites_path, concurrency=8, threads=4):
	stopping, active = asyncio.Event(), {}
	loop = asyncio.get_running_loop()
	for signum in (signal.SIGTERM, signal.SIGINT):
		loop.add_signal_handler(signum, stopping.set)
	with ThreadPoolExecutor(max_workers=threads, thread_name_prefix="bob-tool") as executor:
		context = SiteContext(site, sites_path, executor)
		try:
			while not stopping.is_set():
				for run_id, task in list(active.items()):
					if task.done():
						if not task.cancelled() and (error := task.exception()):
							logger.error("Run %s stopped (%s)", run_id, type(error).__name__)
						active.pop(run_id)
				if len(active) < concurrency:
					for run_id in await context.call(queued_runs, concurrency - len(active)):
						if run_id not in active:
							active[run_id] = asyncio.create_task(RunWorkflow(context, run_id).run())
				with suppress(asyncio.TimeoutError):
					await asyncio.wait_for(stopping.wait(), timeout=1)
		finally:
			for task in active.values():
				task.cancel()
			await asyncio.gather(*active.values(), return_exceptions=True)


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--site", required=True)
	parser.add_argument("--sites-path", required=True)
	parser.add_argument("--concurrency", type=int, default=8)
	parser.add_argument("--threads", type=int, default=4)
	args = parser.parse_args()
	args.sites_path = os.path.abspath(args.sites_path)
	# Frappe's site loggers resolve site-relative paths from the sites directory.
	os.chdir(args.sites_path)
	logging.basicConfig(level=logging.INFO)
	asyncio.run(serve(args.site, args.sites_path, max(1, args.concurrency), max(1, args.threads)))


if __name__ == "__main__":
	main()
