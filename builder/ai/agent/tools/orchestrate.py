"""Orchestration tools — let the dashboard agent parallelize independent work.

Both are `side="server"`: the loop runs the handler and feeds its result back to the
model, which then continues. `spawn_parallel_agents` blocks (inside its handler) until
the fan-out settles; `create_component` is a quick single generation. Neither exists in
the sub-agent registry — a sub-agent cannot spawn (recursion guard) nor is it expected
to author shared components (the parent lays those down first).
"""

import frappe

from builder.ai import orchestration
from builder.ai.agent.registry import Tool


def spawn_parallel_agents(ctx, args: dict) -> str:
	return orchestration.spawn_parallel_agents(ctx, args)


def create_component(ctx, args: dict) -> str:
	kind = (args.get("name") or "Component").strip()
	brief = (args.get("brief") or "").strip()
	if not brief:
		return "Provide a `brief` describing the component to build."
	component_id = orchestration.create_component_asset(kind, brief, ctx.model, ctx.api_key)
	if not component_id:
		return "Component generation produced no blocks — refine the brief and try again."
	return (
		f"Created the '{kind}' component (id {component_id}). In a page, embed it as a block "
		f"`{{el: div, component: {component_id}}}` — put the header FIRST and the footer LAST."
	)


spawn_parallel_agents_tool = Tool(
	name="spawn_parallel_agents",
	side="server",
	description=(
		"Fan out INDEPENDENT work to parallel sub-agents and wait for them all. Use this for "
		"work that decomposes cleanly — e.g. building the several pages of a site, or generating "
		"several posts — so it runs concurrently instead of one-at-a-time. Give each task a "
		"self-contained `instructions` brief. A task with a `page_title` gets a fresh draft page "
		"(under one shared site folder) that its sub-agent builds; put shared design guidance "
		"(theme var names, header/footer component ids, palette, fonts) in `shared_context` so "
		f"every page stays consistent. Max {orchestration.MAX_PARALLEL_TASKS} tasks per call. "
		"ONLY for 2+ genuinely independent tasks — for a single page use create_page + "
		"generate_page directly, never a batch."
	),
	parameters={
		"type": "object",
		"properties": {
			"tasks": {
				"type": "array",
				"items": {
					"type": "object",
					"properties": {
						"title": {"type": "string", "description": "Short label, e.g. 'Home page'."},
						"instructions": {
							"type": "string",
							"description": "A complete, self-contained brief for this task's sub-agent.",
						},
						"page_title": {
							"type": "string",
							"description": "If set, create a draft page with this title for the sub-agent to build.",
						},
						"route": {
							"type": "string",
							"description": "Optional route for the page (defaults from the title).",
						},
					},
					"required": ["title", "instructions"],
				},
			},
			"shared_context": {
				"type": "string",
				"description": "Design guidance prepended to every task (theme tokens, component ids, palette, fonts).",
			},
			"site_name": {
				"type": "string",
				"description": "Optional name for the site folder holding the pages.",
			},
		},
		"required": ["tasks"],
	},
	handler=spawn_parallel_agents,
)

create_component_tool = Tool(
	name="create_component",
	side="server",
	description=(
		"Build ONE reusable component (a shared Header or Footer) and store it as a Builder "
		"Component, returning its id. Create the header and footer BEFORE spawning page builders "
		"so each page can embed them for a consistent site. Applies immediately."
	),
	parameters={
		"type": "object",
		"properties": {
			"name": {"type": "string", "description": "Component name, e.g. 'Header' or 'Footer'."},
			"brief": {
				"type": "string",
				"description": "What the component should contain and how it should look.",
			},
		},
		"required": ["name", "brief"],
	},
	handler=create_component,
)

TOOLS = [spawn_parallel_agents_tool, create_component_tool]
