"""Creating another page, and handing its build to that page's own chat.

Every edit Bob makes lands in the open page's draft, so a request for a different
page ("add a page for Room to Move") can't be built here. create_page makes the
page instead; when this turn ends, the editor opens it and sends the brief as its
chat's first message. The build then runs where it belongs: live on that page's
canvas, revertible like any other turn.
"""

import re

import frappe

from builder.ai.agent.registry import Tool


def create_page(ctx, args: dict) -> str:
	title = (args.get("title") or "").strip()
	brief = (args.get("brief") or "").strip()
	if not title or not brief:
		return "FAILED: create_page needs a title and a brief saying what to build on the page."
	if getattr(ctx, "created_page", None):
		return (
			"FAILED: one new page per turn, since the editor can open only one. Tell the user it "
			"is on its way and that the next page follows when they ask."
		)
	route = (args.get("route") or "").strip().strip("/") or slugify(title)
	if taken := frappe.db.get_value("Builder Page", {"route": route}):
		return (
			f"FAILED: route '/{route}' is already used by page {taken}. Read the site's routes "
			"(query_records 'Builder Page') and pick one that fits the hierarchy."
		)
	try:
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": title,
				"route": route,
				"project_folder": source_page(ctx).get("project_folder"),
			}
		).insert()
	except frappe.PermissionError:
		return "FAILED: this user isn't allowed to create pages. Say so plainly."
	ctx.created_page = page.name
	ctx.emit(
		"open_page",
		new_page_id=page.name,
		title=title,
		prompt=kickoff_prompt(ctx, brief),
		after_commit=True,
	)
	return (
		f"Created '{title}' ({page.name}) at /{route}. When this turn ends, the editor opens it "
		"and builds it from your brief in that page's own chat; don't build it here. End the "
		"turn now with one short sentence saying so."
	)


def kickoff_prompt(ctx, brief: str) -> str:
	"""The brief, plus where it came from: the new chat starts knowing nothing else."""
	source = source_page(ctx)
	if not source:
		return brief
	return f"{brief}\n\n(Asked from the page {source['page_title']}, {ctx.page_id}, at /{source['route']}.)"


def source_page(ctx) -> dict:
	if not ctx.page_id:
		return {}
	return (
		frappe.db.get_value(
			"Builder Page", ctx.page_id, ["page_title", "route", "project_folder"], as_dict=True
		)
		or {}
	)


def slugify(title: str) -> str:
	return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "page"


TOOLS = [
	Tool(
		name="create_page",
		side="server",
		handler=create_page,
		description=(
			"Create another page and hand its build to that page's own chat. Your edits only "
			"ever land on the open page, so this is the one way to make a different page. When "
			"your turn ends, the editor opens the new page and sends `brief` there as its first "
			"message, and the build runs live on that canvas. One page per turn. Don't build its "
			"content here, and don't use this to redesign the open page."
		),
		parameters={
			"type": "object",
			"properties": {
				"title": {"type": "string", "description": "The page title, e.g. 'Room to Move'."},
				"route": {
					"type": "string",
					"description": (
						"URL path without a leading slash, fitted into the site's existing routes "
						"(e.g. 'classes/room-to-move'). Defaults to a slug of the title."
					),
				},
				"brief": {
					"type": "string",
					"description": (
						"The request the new page's chat receives, written as the user would ask it: "
						"what the page is for, its sections and content, and which existing page to "
						"match by page_id. That chat starts fresh and knows only this brief and a "
						"pointer back to the page it came from."
					),
				},
			},
			"required": ["title", "brief"],
		},
	)
]
