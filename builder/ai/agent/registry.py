"""Tool registry for the Builder AI agent.

Every capability the agent has is a `Tool`. A tool declares its OpenAI-style
function schema and a *side* that tells the loop how to handle a call to it:

  - "client":   the operation is applied in the browser (block edits, scripts).
                The loop batches these and emits them to the frontend.
  - "server":   the loop runs `handler(ctx, args)` immediately and feeds the
                returned string back to the model as a tool result, then loops.
  - "terminal": the call ends the turn and hands control back to the user
                (e.g. ask a clarifying question, propose a plan). The loop calls
                `handler(ctx, args)` to emit the appropriate event and stops.

A tool may additionally produce a large *streamed artifact* (e.g. a full page
of YAML). Such a tool sets `artifact` + `generator`: when the conversational
model calls it, the loop hands execution to the generator, which produces the
artifact on the heavy model and streams it to the client as content (reliable),
then returns the canonical client op(s) to apply. The agent calling the tool is
the signal to generate — no out-of-band state decides it.

Adding a capability = registering one `Tool`. The loop never changes.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

ToolSide = Literal["client", "server", "terminal"]


@dataclass
class Tool:
	name: str
	side: ToolSide
	description: str
	parameters: dict
	# Required for "server" and "terminal" tools; ignored for "client" tools.
	# Signature: handler(ctx, args: dict) -> str | None
	handler: Callable | None = None
	# When set, this tool produces a streamed artifact of the given kind (e.g.
	# "page_yaml"). The loop runs `generator(ctx, args) -> list[dict]` instead of
	# emitting a plain client op; the generator streams the artifact as content
	# and returns the canonical client op(s) to apply. None = ordinary tool.
	artifact: str | None = None
	generator: Callable | None = None

	def schema(self) -> dict:
		return {
			"type": "function",
			"function": {
				"name": self.name,
				"description": self.description,
				"parameters": self.parameters,
			},
		}


class ToolRegistry:
	def __init__(self):
		self._tools: dict[str, Tool] = {}

	def register(self, tool: Tool) -> Tool:
		self._tools[tool.name] = tool
		return tool

	def extend(self, tools: list[Tool]) -> None:
		for tool in tools:
			self.register(tool)

	def get(self, name: str) -> Tool | None:
		return self._tools.get(name)

	def side(self, name: str) -> ToolSide:
		tool = self._tools.get(name)
		return tool.side if tool else "client"

	def schemas(self) -> list[dict]:
		return [tool.schema() for tool in self._tools.values()]

	def names(self) -> list[str]:
		return list(self._tools)


def pick(tools: list[Tool], names: set[str]) -> list[Tool]:
	"""Select tools by name — used to compose the headless registries from the same
	module TOOLS lists as the interactive one, without duplicating tool definitions."""
	return [t for t in tools if t.name in names]


def build_default_registry() -> ToolRegistry:
	"""Assemble the registry from the tool modules. Imported lazily to avoid
	import cycles (tool handlers reference the agent context type)."""
	from builder.ai.agent.tools import blocks, conversation, data, generate, query, scripts, settings

	registry = ToolRegistry()
	registry.extend(generate.TOOLS)
	registry.extend(blocks.TOOLS)
	registry.extend(query.TOOLS)
	registry.extend(scripts.TOOLS)
	registry.extend(conversation.TOOLS)
	registry.extend(data.TOOLS)
	registry.extend(settings.TOOLS)
	return registry


def build_orchestrator_registry() -> ToolRegistry:
	"""The page-less dashboard chat. It cannot apply client block/script edits (no
	canvas), so it has NO block tools and does page building via `spawn_parallel_agents`
	(one headless sub-agent per page) after laying down shared assets (theme variables,
	header/footer components). Site-wide + data-model changes stay confirm-gated."""
	from builder.ai.agent.tools import conversation, data, orchestrate, settings

	registry = ToolRegistry()
	registry.extend(conversation.TOOLS)  # ask_clarification, propose_plan
	registry.extend(
		pick(
			data.TOOLS,
			{"list_doctypes", "get_doctype_schema", "query_records", "create_doctype", "seed_sample_data"},
		)
	)
	registry.extend(
		pick(settings.TOOLS, {"set_theme_variable", "set_home_page", "edit_global_settings", "publish_site"})
	)
	registry.extend(orchestrate.TOOLS)  # spawn_parallel_agents, create_component
	return registry


def build_subagent_registry() -> ToolRegistry:
	"""One headless page builder in a fan-out. It generates a page server-side and can
	populate data / page settings / theme tokens — but has NO `spawn_parallel_agents`
	(recursion guard), NO confirm-gated terminal tools (no user to confirm in a worker),
	and NO client block/script tools (nothing to apply them to)."""
	from builder.ai.agent.tools import data, generate, query, scripts, settings

	registry = ToolRegistry()
	registry.extend(generate.TOOLS)  # generate_page → persisted server-side (headless)
	registry.extend(query.TOOLS)  # query_blocks, read_block (on its own page)
	registry.extend(
		pick(data.TOOLS, {"list_doctypes", "get_doctype_schema", "query_records", "write_page_data_script"})
	)
	registry.extend(pick(settings.TOOLS, {"set_page_settings", "set_theme_variable"}))
	registry.extend(pick(scripts.TOOLS, {"get_page_scripts"}))
	return registry
