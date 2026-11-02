"""Suspend orchestration at provider I/O, without parking a Frappe worker or DB connection."""

import copy
from dataclasses import dataclass

MORE = object()


@dataclass
class Delay:
	seconds: float


@dataclass
class ModelRequest:
	model: str
	messages: list
	params: dict
	api_key: str | None = None
	tools: list | None = None
	stream: bool = True
	prepared: dict | None = None
	refresh_auth: object = None

	def prepare(self, asynchronous=False):
		from builder.ai import llm

		if target := llm.codex_route(self.model):
			from builder.ai import codex

			credential = codex.stored_credential(target[0]) if asynchronous else None
			access, account = (
				(credential.get("access"), credential.get("account_id"))
				if credential
				else codex.runtime_auth(target[0])
			)
			self.prepared = {
				"transport": "codex",
				"provider": target[0],
				"credential": credential,
				"url": f"{codex.API_BASE}/codex/responses",
				"headers": codex.request_headers(access, account),
				"payload": codex.build_payload(
					target[1], self.messages, self.tools, self.params.get("reasoning_effort")
				),
			}
			return
		model, overrides, key = llm.route(self.model, self.api_key)
		messages = copy.deepcopy(self.messages)
		llm.patch_messages_for_provider(model, messages)
		params = llm.patch_params_for_provider(model, self.params)
		self.prepared = {
			"transport": "litellm",
			"payload": {
				"model": model,
				"messages": messages,
				"stream": self.stream,
				"api_key": key,
				"num_retries": 0,
				"timeout": 120,
				**({"tools": self.tools} if self.tools else {}),
				**({"stream_options": {"include_usage": True}} if self.stream else {}),
				**llm.provider_kwargs(model),
				**overrides,
				**params,
			},
		}

	def synchronous(self):
		from builder.ai import llm

		if self.tools is not None:
			return llm.complete_with_tools(
				self.model, self.messages, self.tools, self.params, api_key=self.api_key, stream=self.stream
			)
		return llm.complete(self.model, self.messages, self.params, api_key=self.api_key, stream=self.stream)


def consume_stream(request, consume):
	batch = yield request
	while batch is not None:
		for chunk in batch:
			consume(chunk)
		batch = yield MORE


def drive_sync(workflow, checkpoint=None):
	import time

	from builder.ai.scheduling import ReadBatch, perform_read

	stream = None
	value = None
	error = None
	try:
		while True:
			try:
				command = workflow.throw(error) if error else workflow.send(value)
			except StopIteration as done:
				return done.value
			error, value = None, None
			try:
				if checkpoint:
					checkpoint()
				if isinstance(command, Delay):
					time.sleep(command.seconds)
				elif isinstance(command, ReadBatch):
					value = [perform_read(command, op) for op in command.operations]
				elif isinstance(command, ModelRequest):
					if stream and hasattr(stream, "close"):
						stream.close()
					response = command.synchronous()
					if not command.stream:
						value = response
						stream = None
						continue
					stream = iter(response)
				if command is MORE or isinstance(command, ModelRequest):
					chunk = next(stream, None)
					value = [chunk] if chunk is not None else None
					if chunk is None:
						stream = None
			except Exception as exc:
				error = exc
	finally:
		if stream and hasattr(stream, "close"):
			stream.close()
