"""preview_page — let the agent SEE the page it built.

Renders the page's draft to a webp screenshot with the same in-process
headless-Chromium path the publish flow uses, saves it as the page's dashboard
preview thumbnail, surfaces it in the chat (via the activity feed), and hands it
to the vision-capable model so it can catch broken layout before reporting done.
Degrades to a plain "preview unavailable" tool result when no renderer is
reachable — a missing Chromium must never fail the turn."""

import base64
import logging

import frappe

from builder.ai.agent.registry import Tool

logger = frappe.logger("builder.ai.agent.preview")
logger.setLevel(logging.INFO)

MAX_PREVIEWS_PER_TURN = 2  # hard cost bound — a screenshot loop can't run away
MAX_IMAGE_BYTES = 3 * 1024 * 1024  # mirrors BlockCodec.validate_image_data's cap
PREVIEW_WIDTH = 1280
PREVIEW_HEIGHT = 2000  # tall enough to review several sections, not just the hero


def render_page_image(page) -> bytes:
	from builder.html_preview_image import render

	return render(page.get_preview_html(), width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT)


def refresh_page_thumbnail(page) -> None:
	"""Queue the page's OWN preview generation (same as the publish flow) so the
	dashboard/batch thumbnails refresh in the standard card format. The tall
	self-review capture is never saved as the preview — it crops badly on cards."""
	frappe.enqueue_doc(
		page.doctype,
		page.name,
		"generate_page_preview_image",
		queue="short",
		enqueue_after_commit=True,
	)


def attach_to_model(ctx, page, image: bytes) -> bool:
	if len(image) > MAX_IMAGE_BYTES:
		return False
	data_url = "data:image/webp;base64," + base64.b64encode(image).decode()
	caption = f"Screenshot of draft page '{page.page_title or page.name}':"
	ctx.pending_images.append({"caption": caption, "data_url": data_url})
	return True


def run_preview_page(ctx, args: dict) -> str:
	page_id = ((args.get("page_id") or "").strip()) or ctx.page_id
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return f"FAILED: page '{page_id or '(none)'}' not found — open or create a page first."
	if ctx.preview_count >= MAX_PREVIEWS_PER_TURN:
		return "Preview limit reached for this turn — proceed with what you have."
	ctx.preview_count += 1
	page = frappe.get_doc("Builder Page", page_id)
	try:
		image = render_page_image(page)
	except Exception:
		logger.warning("preview_page: render failed for %s", page_id, exc_info=True)
		return (
			"Preview unavailable (screenshot renderer not reachable). "
			"Continue without the visual check — do not retry."
		)
	refresh_page_thumbnail(page)
	# A text-only model can't receive the image — attaching it kills the whole turn
	# (OpenRouter: "No endpoints found that support image input"). The screenshot
	# still refreshed the page thumbnail above; just skip the visual review.
	from builder.ai.models import ModelRegistry

	if not ModelRegistry.supports_vision(ctx.loop_model):
		return (
			"Screenshot saved as the page's thumbnail, but your selected model can't view "
			"images — skip the visual check and continue."
		)
	attached = attach_to_model(ctx, page, image)
	if not attached:
		return "Screenshot captured but too large to attach for review — finish up."
	return (
		"Screenshot attached below — for YOUR eyes only (the user doesn't see it). Review it "
		"ONCE: fix only obvious breakage (unreadable contrast, overlapping or empty sections), "
		"then finish. Don't describe the screenshot to the user."
	)


preview_page = Tool(
	name="preview_page",
	side="server",
	handler=run_preview_page,
	description=(
		"Render a page's draft to a screenshot attached to you so you can SEE what you "
		"built (also refreshes the page's dashboard thumbnail — the user is not shown the "
		"image in chat). Use it once after generate_page or a major edit for a single "
		"self-review pass — fix only obvious visual breakage, never loop screenshots. If "
		"the renderer is unavailable, continue without it."
	),
	parameters={
		"type": "object",
		"properties": {
			"page_id": {
				"type": "string",
				"description": "The page to screenshot. Defaults to the page you have open.",
			},
		},
	},
)

TOOLS = [preview_page]
