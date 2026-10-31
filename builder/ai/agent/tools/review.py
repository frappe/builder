"""A fresh review of a page Bob just built: a separate model call that sees only the
request, the direction contract and screenshots, never Bob's conversation, so it
judges the page rather than Bob's account of it (Impeccable's finish reviewer)."""

import base64
import logging

import frappe

from builder.ai import llm
from builder.ai.prompts import Prompts

logger = frappe.logger("builder.ai.agent.review")
logger.setLevel(logging.INFO)

REVIEWER = (
	"""You review a web page someone else just built, for the person who asked for it. You know only their request, the direction contract the page was built to, and screenshots: desktop first, then mobile, each top to bottom.

Your first word is the disposition, exactly one of:
- ship: the page carries the contract and nothing material is broken.
- fix: the contract holds, but specific things fall short.
- rebuild: the page does not carry the contract's thesis or world.

Then at most five findings, most material first, one line each: where on the page, what falls short of the contract or the request, and the concrete edit that fixes it (a size, a colour, a line of copy, a layout change). Judge in this order:
1. First viewport: does it show the THESIS at the scale FIRST VIEWPORT describes, with the primary action where it says?
2. OWN-WORLD: would the page be recognisable with its content removed, or is it a template in the contract's colours?
3. STORY: does the page read in the contract's order and end on a real close?
4. Substance: copy that could describe anyone's project or business ("A project from my work", "We care about quality") is filler, and a section made of it is a finding; so is a section that only states a placeholder.
5. Breakage: unreadable contrast, overlap, clipping, empty or orphaned boxes, text in a fallback serif no block chose, a mobile layout that collapses.
6. The AI tells below.
Judge only what the screenshots show; motion and hover are invisible in them. No praise, no preamble.

"""
	+ Prompts.AI_TELLS
)


def fresh_review(ctx, page, desktop: bytes, color_scheme: str, contract: str) -> str:
	from builder.ai.agent.tools.preview import render_page_image, tile_screenshot

	try:
		mobile = render_page_image(page, "mobile", color_scheme)
		tiles = [tile for capture in (desktop, mobile) for tile in tile_screenshot(capture)[0]]
		verdict = llm.complete(
			ctx.model,
			review_messages(ctx.prompt, contract, tiles),
			llm.TASK_PARAMS["complex"],
			stream=False,
			api_key=ctx.api_key,
		)
	except Exception:
		logger.warning("fresh_review: failed for %s", page.name, exc_info=True)
		return "The fresh review couldn't run; judge the screenshot against your contract yourself."
	ctx.reviews.append(verdict := (verdict or "").strip())
	return (
		"Fresh review (the reviewer saw only the request, your contract and desktop and mobile "
		f"screenshots):\n{verdict}"
	)


def review_messages(request: str, contract: str, tiles: list[bytes]) -> list[dict]:
	images = [
		{"type": "image_url", "image_url": {"url": "data:image/webp;base64," + base64.b64encode(t).decode()}}
		for t in tiles
	]
	text = f"The request:\n{request}\n\nThe direction contract:\n{contract}"
	return [
		{"role": "system", "content": REVIEWER},
		{"role": "user", "content": [{"type": "text", "text": text}, *images]},
	]
