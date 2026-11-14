"""New pages. Bob only proposes one: the page is created when the user confirms
the card at the end of the turn (agent/page_changes.py), and built the turn after."""

from builder.ai.agent.registry import Tool


def run_create_page(ctx, args: dict) -> str:
	return ctx.page_changes.propose_page(args.get("title"), args.get("route"), args.get("brief"))


create_page = Tool(
	name="create_page",
	side="server",
	handler=run_create_page,
	description=(
		"Propose a NEW page for this site, only when the user asks for another page (an empty open "
		"page is built in place with generate_page). Nothing is created now: the user confirms on a "
		"card when your turn ends, and you build it in the turn after, from `brief`, without "
		"touching their canvas. Read the site's routes first and fit this one into them."
	),
	parameters={
		"type": "object",
		"properties": {
			"title": {"type": "string", "description": "The page title, e.g. 'Careers'."},
			"route": {"type": "string", "description": "A free URL path, e.g. 'careers' or 'menu/drinks'."},
			"brief": {
				"type": "string",
				"description": (
					"What the page holds, as you'd brief generate_page: purpose, sections, the site "
					"page whose look it should match. Shown to the user on the card."
				),
			},
		},
		"required": ["title", "route", "brief"],
	},
)

TOOLS = [create_page]
