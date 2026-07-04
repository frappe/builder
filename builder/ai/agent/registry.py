"""Tool registry for the Builder AI agent.

Every capability the agent has is a `Tool`. A tool declares its OpenAI-style
function schema and a *side* that tells the loop how to handle a call to it:

  - "client":   a page edit (block ops, scripts). The loop applies it to the
                authoritative server-side WorkingTree first, then mirrors the
                accepted ops to the editor canvas (a live view).
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
	from builder.ai.agent.tools import (
		blocks,
		codebase,
		conversation,
		data,
		generate,
		orchestrate,
		pages,
		preview,
		query,
		sandbox,
		scripts,
		settings,
	)

	registry = ToolRegistry()
	registry.extend(generate.TOOLS)
	registry.extend(blocks.TOOLS)
	registry.extend(query.TOOLS)
	registry.extend(scripts.TOOLS)
	registry.extend(conversation.TOOLS)
	registry.extend(data.TOOLS)
	registry.extend(settings.TOOLS)
	# Whole-site capabilities in the editor: focus/create/manage other pages,
	# screenshot self-review, and parallel fan-out for multi-page builds.
	registry.extend(pages.TOOLS)
	registry.extend(preview.TOOLS)
	registry.extend(orchestrate.TOOLS)
	# Primitives from the codebase-context experiment: run_python covers bulk or
	# unusual page mutations the block tools don't express well, and source access
	# lets the model check Builder mechanics instead of guessing.
	registry.extend(codebase.TOOLS)
	registry.extend(sandbox.TOOLS)
	return registry


def headless_page_tools() -> list[Tool]:
	"""The page capabilities every HEADLESS agent gets: focus a page (open/create),
	read any page, generate a full page, edit it surgically with the block tools
	(applied server-side by the mutating WorkingTree), query its structure, and
	screenshot it for a self-review pass."""
	from builder.ai.agent.tools import blocks, generate, pages, preview, query

	return [*pages.TOOLS, *generate.TOOLS, *blocks.TOOLS, *query.TOOLS, *preview.TOOLS]


def build_orchestrator_registry() -> ToolRegistry:
	"""The page-less dashboard chat — the full builder. It reads/creates/edits/
	generates single pages inline (headless page tools) and reserves
	`spawn_parallel_agents` for genuinely parallel multi-page work, after laying
	down shared assets (theme variables, header/footer components). Site-wide +
	data-model changes stay confirm-gated."""
	from builder.ai.agent.tools import conversation, data, orchestrate, scripts, settings

	registry = ToolRegistry()
	registry.extend(conversation.TOOLS)  # present_ui
	registry.extend(headless_page_tools())
	registry.extend(scripts.TOOLS)  # set/update apply via their headless handlers
	registry.extend(
		pick(
			data.TOOLS,
			{
				"list_doctypes",
				"get_doctype_schema",
				"query_records",
				"get_document",
				"write_page_data_script",
				"create_doctype",
				"seed_sample_data",
			},
		)
	)
	registry.extend(
		pick(
			settings.TOOLS,
			{
				"set_theme_variable",
				"set_page_settings",
				"set_home_page",
				"edit_global_settings",
				"publish_site",
			},
		)
	)
	registry.extend(orchestrate.TOOLS)  # spawn_parallel_agents, create_component
	return registry


def build_subagent_registry() -> ToolRegistry:
	"""One headless page builder in a fan-out. Same page capabilities as the
	orchestrator minus focus-switching (open_page/create_page — a child stays on its
	assigned page; read_page covers references), with NO `spawn_parallel_agents`
	(recursion guard) and NO confirm-gated terminal tools (no user to confirm in a
	worker)."""
	from builder.ai.agent.tools import data, scripts, settings

	registry = ToolRegistry()
	# No focus-switching, and no confirm-gated lifecycle (nobody to confirm in a worker).
	registry.extend(
		[t for t in headless_page_tools() if t.name not in {"open_page", "create_page", "manage_pages"}]
	)
	registry.extend(
		pick(
			data.TOOLS,
			{
				"list_doctypes",
				"get_doctype_schema",
				"query_records",
				"get_document",
				"write_page_data_script",
			},
		)
	)
	registry.extend(pick(settings.TOOLS, {"set_page_settings", "set_theme_variable"}))
	registry.extend(scripts.TOOLS)  # set/update apply via their headless handlers
	return registry
