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


def attach_to_chat(ctx, page, image: bytes) -> None:
	"""Save as the page's preview file — the dashboard thumbnail updates for free —
	and pin the URL on the current activity entry so the chat renders it inline."""
	from builder.utils import get_builder_page_preview_file_paths

	public_path, local_path = get_builder_page_preview_file_paths(page)
	with open(local_path, "wb") as f:
		f.write(image)
	page.db_set("preview", public_path, commit=True, update_modified=False)
	if ctx.current_activity is not None:
		ctx.current_activity["image_url"] = public_path


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
	attach_to_chat(ctx, page, image)
	attached = attach_to_model(ctx, page, image)
	if not attached:
		return "Screenshot captured and shown to the user (too large to attach for review) — finish up."
	return (
		"Screenshot captured — it's shown to the user and attached below for you. Review it "
		"ONCE: fix only obvious breakage (unreadable contrast, overlapping or empty sections), "
		"then finish. Don't re-describe the screenshot to the user."
	)


preview_page = Tool(
	name="preview_page",
	side="server",
	handler=run_preview_page,
	description=(
		"Render a page's draft to a screenshot: shown to the user in the chat, and attached "
		"to you so you can SEE what you built. Use it once after generate_page or a major "
		"edit for a single self-review pass — fix only obvious visual breakage, never loop "
		"screenshots. If the renderer is unavailable, continue without it."
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
