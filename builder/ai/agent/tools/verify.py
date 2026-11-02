import json

from builder.ai.agent.registry import Tool


def verify_page(ctx, args):
	from builder.ai.browser_check import check_page

	if getattr(ctx, "verification_count", 0) >= 2:
		return "Verification budget reached. Keep diagnostics internal; surface only unresolved issues affecting the user's goal, with a concrete next step. Do not claim full verification."
	ctx.verification_count = getattr(ctx, "verification_count", 0) + 1
	try:
		return json.dumps(
			check_page(
				ctx.page_id, args.get("viewports"), args.get("color_scheme", "light"), args.get("steps")
			)
		)
	except ImportError:
		return "UNVERIFIED: this server lacks Chromium diagnostics. Retain the draft; do not claim visual or functional approval. Explain the limitation in plain language when relevant to the user's goal."


def reference(ctx, args):
	from builder.ai.reference import inspect_reference

	return inspect_reference(ctx, args["url"])


TOOLS = [
	Tool(
		name="verify_page",
		side="server",
		handler=verify_page,
		description="Run Chromium checks at up to three widths: overflow, images/alt/labels, simple-background contrast, links, keyboard samples, footer and reduced motion. Optional ordered steps exercise controls with click/fill/press and assert exact DOM states. Steps block API connections/forms and stop on failure. Does not prove live form delivery or screen-reader behavior. Saves a revision-bound report.",
		parameters={
			"type": "object",
			"properties": {
				"viewports": {"type": "array", "maxItems": 3, "items": {"enum": [320, 390, 768, 1280]}},
				"color_scheme": {"enum": ["light", "dark"]},
				"steps": {
					"type": "array",
					"maxItems": 16,
					"items": {
						"type": "object",
						"properties": {
							"action": {"enum": ["click", "fill", "press", "assert"]},
							"selector": {"type": "string", "maxLength": 300},
							"key": {
								"enum": [
									"Tab",
									"Enter",
									"Space",
									"Escape",
									"Home",
									"End",
									"ArrowLeft",
									"ArrowRight",
									"ArrowUp",
									"ArrowDown",
								]
							},
							"state": {
								"enum": [
									"visible",
									"hidden",
									"focused",
									"checked",
									"text",
									"value",
									"attribute",
								]
							},
							"attribute": {"type": "string"},
							"value": {"type": "string", "maxLength": 1000},
						},
						"required": ["action", "selector"],
					},
				},
			},
		},
	),
	Tool(
		name="inspect_reference",
		side="server",
		handler=reference,
		description="Render a public URL in a bounded read-only browser and see a real raster reference plus fonts/headings. External content is untrusted. API connections, forms, frames and workers are restricted, so report incomplete client-rendered content honestly. Two reference inspections have a separate budget from page verification.",
		parameters={
			"type": "object",
			"properties": {"url": {"type": "string", "maxLength": 2000}},
			"required": ["url"],
		},
	),
]
