"""The studio intake: a small agent that runs while a page is still empty. It asks a
few visual, easy rounds, writes a detailed prompt, and hands it to Bob with
start_build; Bob then builds the page from that prompt in the same job. Switched on
per site by the `bob_studio` site config flag."""

import json
import os

import frappe

from builder.ai.agent.registry import Tool, ToolRegistry
from builder.ai.prompts import Prompts

DIR = os.path.dirname(__file__)
# Bob's new-page skill reads this opening as a finished intake: build, no cards
BRIEF_OPENING = "Studio brief, from the intake. Build it now.\n\n"
STUDIO_TOOLS = ("present_ui", "search_images", "read_url", "research")
# a brief without these builds a template; start_build refuses it
REQUIRED_PARTS = ("## Concept", "## Interactions", "## Sections")
MIN_BRIEF_CHARS = 600


class Studio:
	@staticmethod
	def wanted(page_id: str | None) -> bool:
		from builder.ai import page_writer

		if not page_id or not frappe.conf.get("bob_studio"):
			return False
		root = page_writer.load_page_root(page_id)
		return not (root and root.get("children"))

	@staticmethod
	def system_prompt() -> str:
		with open(os.path.join(DIR, "prompt.md")) as f:
			prompt = f.read()
		return prompt.replace("{VOICE}", Prompts.VOICE).replace("{PRESETS}", presets_text())

	@staticmethod
	def registry() -> ToolRegistry:
		from builder.ai.agent.registry import build_default_registry

		bob = build_default_registry()
		registry = ToolRegistry()
		for name in STUDIO_TOOLS:
			registry.register(bob.get(name))
		registry.register(start_build)
		return registry


def interaction_pass(brief: str, page_id: str | None) -> str | None:
	"""The follow-up turn that builds a brief's interactions, when Bob's build left the
	page without JavaScript: a page that promises an interaction and has none is dead."""
	if not page_id or "## Interactions" not in brief or has_javascript(page_id):
		return None
	interactions = brief.split("## Interactions", 1)[1].split("\n## ", 1)[0].strip()
	return (
		"Now build the page's interactions from the studio brief, as page scripts: the CSS and the "
		"JavaScript in one round. The page is built, so read_block the elements each one needs first, "
		"add the class hooks to blocks that lack them, then set_page_script. Every button or control on "
		"the page that promises an interaction must work when you're done, or go. A screenshot can't "
		"show movement, so don't preview to check it; say what you wired and how to try it.\n\n"
		f"## Interactions\n{interactions}"
	)


def has_javascript(page_id: str) -> bool:
	scripts = [
		row.builder_script for row in frappe.get_doc("Builder Page", page_id).get("client_scripts") or []
	]
	return bool(scripts) and frappe.db.exists(
		"Builder Client Script", {"name": ["in", scripts], "script_type": "JavaScript"}
	)


def presets_text() -> str:
	with open(os.path.join(DIR, "presets.json")) as f:
		presets = json.load(f)
	return "\n".join(
		f"- {p['name']}: {p['feel']}. Palette {', '.join(f'{role} {hex}' for role, hex in p['palette'].items())}. "
		f"Faces {p['faces']}. Layout {p['layout']}. Interaction: {p['interaction']}. "
		f"Photo query '{p['image_query']}'. Suits {p['suits']}."
		for p in presets
	)


def run_start_build(ctx, args: dict) -> str | None:
	from builder.ai.session import AISession

	prompt = (args.get("prompt") or "").strip()
	missing = [part for part in REQUIRED_PARTS if part not in prompt]
	if len(prompt) < MIN_BRIEF_CHARS or missing:
		return (
			f"FAILED: that prompt can't be built into a page worth remembering{': it has no ' + ', '.join(missing) if missing else ''}. "
			"Write all of it: Concept, Interactions, Direction, Sections with their copy, Media, Avoid and Placeholders."
		)
	title = prompt.splitlines()[0].lstrip("# ").strip()
	ctx.handoff = BRIEF_OPENING + prompt
	AISession.try_append_message(
		ctx.session_id,
		"user",
		ctx.handoff,
		message_type="chat",
		task_type="agent",
		metadata={"displayText": f"Studio brief: {title}"[:300]},
	)
	ctx.emit("progress", message="Brief ready. Bob is building it…")
	return None


start_build = Tool(
	name="start_build",
	side="terminal",
	handler=run_start_build,
	description=(
		"Hand the finished prompt to Bob, who builds the page from it straight away. Call it once "
		"the intake has what the page needs, or the moment the person says to just build. Ends "
		"the intake."
	),
	parameters={
		"type": "object",
		"properties": {
			"prompt": {
				"type": "string",
				"description": "The full markdown prompt, in the shape your instructions give.",
			}
		},
		"required": ["prompt"],
	},
)
