"""preview_page — let the agent SEE the page it built.

Renders the page's draft to a webp screenshot with the same in-process
headless-Chromium path the publish flow uses, saves it as the page's dashboard
preview thumbnail, surfaces it in the chat (via the activity feed), and hands it
to the vision-capable model so it can catch broken layout before reporting done.
Degrades to a plain "preview unavailable" tool result when no renderer is
reachable — a missing Chromium must never fail the turn."""

import base64
import html
import logging

import frappe

from builder.ai.agent.registry import Tool

logger = frappe.logger("builder.ai.agent.preview")
logger.setLevel(logging.INFO)

MAX_PREVIEWS_PER_TURN = 2  # hard cost bound — a screenshot loop can't run away
MAX_IMAGE_VIEWS_PER_TURN = 3
MAX_IMAGE_BYTES = 3 * 1024 * 1024  # mirrors BlockCodec.validate_image_data's cap
VIEWPORTS = {"desktop": (1280, 900), "tablet": (768, 1024), "mobile": (390, 844)}
COLOR_SCHEMES = ("light", "dark")
# The tallest document captured; generated pages run 2500-6000px.
CAPTURE_HEIGHT = 8000
# One attached image per this many pixels of page. NOT one tall image: a vision
# model shrinks an image to fit its longest edge (~1568px), so a single
# 1280x6000 capture reaches the model at ~250px wide with every label
# illegible — which is exactly how a page gets reviewed without being read.
# At this height a tile lands near 1:1 and the copy stays readable.
TILE_HEIGHT = 2000
MAX_TILES = 3


MAX_CONTRAST_LINES = 20
# light then dark on one render: the root's data-prefers-color-scheme flips light-dark() tokens
CONTRAST_CHECK = r"""() => {
  const parse = (c) => {
    let m = c.match(/^rgba?\(([^)]+)\)/);
    if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; }
    m = c.match(/^color\(srgb ([^)]+)\)/);
    if (m) { const p = m[1].split(/[\s\/]+/).filter(Boolean).map(parseFloat); return {r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1}; }
    return null;
  };
  const over = (top, under) => ({r: top.r * top.a + under.r * (1 - top.a), g: top.g * top.a + under.g * (1 - top.a), b: top.b * top.a + under.b * (1 - top.a), a: 1});
  const lum = (c) => [c.r, c.g, c.b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }).reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
  const hex = (c) => '#' + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const behind = (el, dark) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage !== 'none') return null;
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; }
    }
    let out = layers.length && layers[layers.length - 1].a >= 1 ? layers.pop() : (dark ? {r: 18, g: 18, b: 18, a: 1} : {r: 255, g: 255, b: 255, a: 1});
    while (layers.length) out = over(layers.pop(), out);
    return out;
  };
  const items = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName)) continue;
    const own = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join(' ').replace(/\s+/g, ' ').trim();
    const text = own || (['INPUT', 'TEXTAREA'].includes(el.tagName) ? (el.value || el.placeholder || '').trim() : '');
    if (!text) continue;
    const box = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (box.width < 1 || box.height < 1 || cs.visibility === 'hidden' || Number(cs.opacity) === 0) continue;
    items.push({el, text: text.slice(0, 60), tag: el.tagName.toLowerCase()});
  }
  const measure = (dark) => items.map(({el}) => {
    const cs = getComputedStyle(el); let fg = parse(cs.color); const bg = behind(el, dark);
    if (!fg || !bg || fg.a === 0) return null;
    const own = cs.color;
    if (fg.a < 1) fg = over(fg, bg);
    const [a, b] = [lum(fg), lum(bg)];
    const size = parseFloat(cs.fontSize); const large = size >= 24 || (parseInt(cs.fontWeight) >= 700 && size >= 18.66);
    return {own, fg: hex(fg), bg: hex(bg), ratio: Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 10) / 10, need: large ? 3 : 4.5};
  });
  // a transition would hand back the old theme's colour for its first frame
  const still = document.createElement('style');
  still.textContent = '*, *::before, *::after { transition: none !important; animation: none !important; }';
  document.head.appendChild(still);
  const root = document.documentElement; const before = root.getAttribute('data-prefers-color-scheme');
  root.setAttribute('data-prefers-color-scheme', 'light'); const light = measure(false);
  root.setAttribute('data-prefers-color-scheme', 'dark'); const dark = measure(true);
  if (before === null) root.removeAttribute('data-prefers-color-scheme'); else root.setAttribute('data-prefers-color-scheme', before);
  still.remove();
  const seen = new Set(); const out = [];
  items.forEach((item, i) => {
    for (const [scheme, m, other] of [['light', light[i], dark[i]], ['dark', dark[i], light[i]]]) {
      if (!m || m.ratio >= m.need) continue;
      const key = [scheme, item.text, m.fg, m.bg].join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({scheme, text: item.text, tag: item.tag, fg: m.fg, bg: m.bg, ratio: m.ratio, fgFixed: !!other && other.own === m.own, bgFixed: !!other && other.bg === m.bg});
    }
  });
  return out;
}"""


def render_page_image(page, viewport: str = "desktop", color_scheme: str | None = None) -> bytes:
	return render_markup_image(page.get_preview_html(color_scheme=color_scheme), viewport)


def render_markup_image(markup: str, viewport: str = "desktop") -> bytes:
	from builder.html_preview_image import render_full_page

	width, height = VIEWPORTS[viewport]
	return render_full_page(markup, width=width, height=height, max_height=CAPTURE_HEIGHT)


def capture_with_contrast(markup: str, viewport: str) -> tuple[bytes, list[dict] | None]:
	"""The screenshot, plus the text it leaves unreadable in light or dark mode; None
	when that couldn't be measured."""
	from builder.html_preview_image import evaluate, render_full_page

	width, height = VIEWPORTS[viewport]
	found = {}

	def inspect(page):
		try:
			found["rows"] = evaluate(page, CONTRAST_CHECK)
		except Exception:
			logger.warning("preview_page: contrast check failed", exc_info=True)

	image = render_full_page(markup, width=width, height=height, max_height=CAPTURE_HEIGHT, inspect=inspect)
	return image, found.get("rows")


def contrast_note(rows: list[dict] | None) -> str:
	"""The measured unreadable text, for the model to fix. Dark mode counts only when
	visitors can get it: the site follows their theme unless auto dark mode is off."""
	if rows and frappe.db.get_single_value("Builder Settings", "disable_auto_dark_mode"):
		rows = [row for row in rows if row["scheme"] == "light"]
	if not rows:
		return ""
	lines = [contrast_line(row) for row in rows[:MAX_CONTRAST_LINES]]
	if len(rows) > MAX_CONTRAST_LINES:
		lines.append(f"- and {len(rows) - MAX_CONTRAST_LINES} more")
	return (
		"\n\nUnreadable text, measured on this render in light and dark mode (visitors get the one "
		"their device uses):\n" + "\n".join(lines) + "\nA colour that stays fixed next to one that "
		"changes with the theme is the cause: give the text and the background behind it both "
		"tokens (a dark block is background on the ink token, text on the paper token), or keep "
		"both fixed. Fix these before you finish. This list already covers both themes, so a "
		"dark capture isn't needed to find them; keep a preview to confirm the fix."
	)


def contrast_line(row: dict) -> str:
	def side(fixed: bool) -> str:
		return "stays fixed" if fixed else "changes with the theme"

	return (
		f'- {row["scheme"]} mode, {row["tag"]} "{row["text"]}": text {row["fg"]} {side(row["fgFixed"])}, '
		f"background {row['bg']} {side(row['bgFixed'])} ({row['ratio']}:1)"
	)


def page_error(page, error: Exception) -> str:
	"""The page raised before any screenshot: the same error its visitors get, so say it."""
	from builder.ai.agent.tools.data import ScriptError

	return (
		"FAILED: the page itself fails to render, so its visitors get the error below too. Fix "
		f"it, then preview again.\n{ScriptError(error, page.page_data_script)}"
	)


# How far a pixel may drift from the background before it counts as content. The
# tail of a webp capture is NOT one flat colour — lossy compression leaves a
# couple of levels of drift across a blank band (measured: 245,222,194 at the
# edge against 243,223,196 across), so an exact match finds "content" everywhere
# and trims nothing.
BLANK_TOLERANCE = 16


def content_height(im) -> int:
	"""Where the page actually ends. Everything below is the blank tail of an
	oversized viewport; measuring it beats guessing a height that either crops a
	page or pads it with emptiness. A whole-image diff against the trailing
	background colour, which is a C-speed operation."""
	from PIL import Image, ImageChops

	background = Image.new("RGB", im.size, im.getpixel((im.width // 2, im.height - 1)))
	drift = ImageChops.difference(im, background).convert("L")
	bbox = drift.point(lambda level: 255 if level > BLANK_TOLERANCE else 0).getbbox()
	return bbox[3] if bbox else im.height


def tile_screenshot(image: bytes) -> tuple[list[bytes], bool]:
	"""Trim the blank tail, then slice the page into readable screenfuls.
	Returns (tiles, complete) — complete is False when the page ran past
	MAX_TILES, so the model can be told it hasn't seen the whole thing."""
	from io import BytesIO

	from PIL import Image

	im = Image.open(BytesIO(image)).convert("RGB")
	im = im.crop((0, 0, im.width, max(content_height(im), 1)))
	tiles = []
	for top in range(0, im.height, TILE_HEIGHT):
		buffer = BytesIO()
		im.crop((0, top, im.width, min(top + TILE_HEIGHT, im.height))).save(buffer, "WEBP", quality=80)
		tiles.append(buffer.getvalue())
		if len(tiles) == MAX_TILES:
			break
	return tiles, len(tiles) * TILE_HEIGHT >= im.height


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


def attach_to_model(ctx, page, image: bytes, variant: str) -> tuple[int, bool]:
	"""Attach the page as a run of readable screenfuls, top to bottom. Returns
	(tiles attached, whether they cover the whole page)."""
	try:
		tiles, complete = tile_screenshot(image)
	except Exception:
		logger.warning("preview_page: tiling failed, attaching the raw capture", exc_info=True)
		tiles, complete = [image], True
	title = page.page_title or page.name
	attached = 0
	for index, tile in enumerate(tiles, start=1):
		if len(tile) > MAX_IMAGE_BYTES:
			continue
		where = f" — part {index} of {len(tiles)}, top to bottom" if len(tiles) > 1 else ""
		ctx.pending_images.append(
			{
				"caption": f"Screenshot of draft page '{title}' ({variant}){where}:",
				"data_url": "data:image/webp;base64," + base64.b64encode(tile).decode(),
			}
		)
		attached += 1
	return attached, complete and attached == len(tiles)


def run_preview_page(ctx, args: dict) -> str:
	from builder.ai.agent.tools.query import resolve_page_reference

	page_id = ctx.page_id
	if ref := (args.get("page_id") or "").strip():
		page_id, why = resolve_page_reference(ref)
		if page_id is None:
			return f"FAILED: {why}."
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return "FAILED: no page in context — open or create a page first."
	if ctx.preview_count >= MAX_PREVIEWS_PER_TURN:
		return "Preview limit reached for this turn — proceed with what you have."
	page = frappe.get_doc("Builder Page", page_id)
	viewport = args.get("viewport") if args.get("viewport") in VIEWPORTS else "desktop"
	color_scheme = args.get("color_scheme") if args.get("color_scheme") in COLOR_SCHEMES else "light"
	variant = f"{viewport}, {color_scheme} mode"
	try:
		markup = page.get_preview_html(color_scheme=color_scheme)
	except Exception as error:
		logger.warning("preview_page: %s failed to render", page_id, exc_info=True)
		return page_error(page, error)
	ctx.preview_count += 1
	try:
		image, unreadable = capture_with_contrast(markup, viewport)
	except Exception:
		logger.warning("preview_page: render failed for %s", page_id, exc_info=True)
		return (
			"Preview unavailable (screenshot renderer not reachable). "
			"Continue without the visual check — do not retry."
		)
	refresh_page_thumbnail(page)
	note = contrast_note(unreadable) if page_id == ctx.page_id else ""
	# A text-only model can't receive the image — attaching it kills the whole turn
	# (OpenRouter: "No endpoints found that support image input"). The screenshot
	# still refreshed the page thumbnail above; just skip the visual review.
	from builder.ai.models import ModelRegistry

	if not ModelRegistry.supports_vision(ctx.loop_model):
		return (
			"Screenshot saved as the page's thumbnail, but your selected model can't view "
			"images — skip the visual check and continue."
		) + note
	attached, complete = attach_to_model(ctx, page, image, variant)
	if not attached:
		return "Screenshot captured but too large to attach for review — finish up."
	extent = (
		f"The page is attached below as {attached} images ({variant}), top to bottom — review ALL of them."
		if attached > 1
		else f"Screenshot attached below ({variant})."
	)
	if not complete:
		extent += " They stop before the end of the page; anything past that you have NOT seen."
	# A screenshot of ANOTHER page is a reference to study, not a build to review —
	# the self-review rubric below would send the model off editing blocks it can't reach.
	if page_id != ctx.page_id:
		return (
			f"{extent} This is another page of the site, attached as a visual REFERENCE for "
			"your eyes only. Study its design language — palette, typography, spacing rhythm, "
			"section structure, imagery treatment — and carry the exact values into your work "
			"on the open page (read_page gives you the precise fonts/hexes/handles). Its "
			"blocks are not editable from here."
		)
	return (
		f"{extent} For your eyes only (the user doesn't see it). Review in two passes, then act:\n"
		"1. Breakage: unreadable contrast, accidental overlap, empty sections, a layout that "
		"collapses. Fonts: the page default is Inter, so text in a Times-like serif that no "
		"block chose means a named family isn't loading on this site; restyle to a family "
		"that resolves here (a real Google Fonts name or an installed User Font). Stale "
		"chrome: an embedded component still showing its default content (a breadcrumb "
		"reading 'Home', another product's name in the nav); override the instance's "
		"children (edit_page on its instance refs) so it names this page. Orphaned "
		"content: an empty styled box with its intended content stacked outside it means "
		"children landed as siblings of their container; `move` them into it.\n"
		"2. Generated look, six yes/no checks: (a) is the signature move visible? (b) are "
		"sections structurally distinct (widths, grids, densities), not one centred column "
		"with background swaps? (c) does the largest text read at least ~3.5x the body size? "
		"(d) are photos treated (scrim, duotone, knockout, frame) rather than plain "
		"rectangles? (e) does the page look like the brief's named concept? (f) is it free of "
		"AI tells (an eyebrow over every heading, gradient headline text, purple-to-pink "
		"gradients, glassmorphism or glowing blobs, an icon tile on every item, the same "
		"rounded card on everything, stock phrases, invented stats or testimonials)?\n"
		"Fix failures with surgical edits on the specific blocks (edit_page, "
		"set_page_script), never by regenerating the page. If a fix changes layout or "
		"structure, spend your remaining preview confirming it landed before you summarize. "
		"Motion and hover are invisible in a static screenshot; don't chase them here. If "
		"two or more checks still fail after your fixes, say so honestly in your summary. "
		"Don't describe the screenshot to the user."
	) + note


preview_page = Tool(
	name="preview_page",
	side="server",
	handler=run_preview_page,
	description=(
		"Render a page's draft to a screenshot attached to you so you can SEE what you "
		"built (also refreshes the page's dashboard thumbnail — the user is not shown the "
		"image in chat). Call it after EVERY generate_page build: it returns a review "
		"rubric (breakage + template-fingerprint checks); fix failures with surgical "
		"block/script edits, preview once more to confirm layout fixes, never loop "
		"screenshots. Also "
		"works on ANOTHER page (pass its page_id) to study it as a visual reference — do "
		"that BEFORE designing a page that must match it, paired with read_page for the "
		"exact values. If the renderer is unavailable, continue without it. Pick "
		"viewport and color_scheme to check the case you changed: a mobile fix at mobile, "
		"a dark-mode change in dark. Never report a mobile or dark-mode change as done "
		"from a desktop light capture. Every capture also measures text against the colour "
		"behind it in light and dark mode and lists what's unreadable."
	),
	parameters={
		"type": "object",
		"properties": {
			"page_id": {
				"type": "string",
				"description": "The page to screenshot. Defaults to the page you have open.",
			},
			"viewport": {
				"type": "string",
				"enum": list(VIEWPORTS),
				"description": "Screen width to render at: desktop (1280px, default), tablet (768px) or mobile (390px).",
			},
			"color_scheme": {
				"type": "string",
				"enum": list(COLOR_SCHEMES),
				"description": "Render in light (default) or dark mode.",
			},
		},
	},
)


def image_view_html(src: str) -> str:
	return (
		'<!doctype html><html><body style="margin:0;height:100vh;display:grid;'
		'place-items:center;background:#808080">'
		f'<img style="width:100%;height:100%;object-fit:contain" src="{html.escape(src, quote=True)}">'
		"</body></html>"
	)


def renderable_source(src: str) -> str | None:
	"""What the renderer may load for an image, or None. Only what the user could
	open themselves gets through (it ends up in front of an external model): data:
	images, public site files, private files they may read, and public web images,
	which are inlined so Chromium never dials the network for them."""
	from urllib.parse import urlparse

	if src.startswith("data:image/"):
		return src
	parsed = urlparse(src)
	if parsed.scheme in ("http", "https") and parsed.netloc != urlparse(frappe.utils.get_url()).netloc:
		return inline_remote_image(src)
	if parsed.path.startswith("/private/files/"):
		name = frappe.db.get_value("File", {"file_url": parsed.path}, "name")
		return src if name and frappe.get_doc("File", name).has_permission("read") else None
	return src if parsed.path.startswith("/files/") else None


def inline_remote_image(src: str) -> str | None:
	"""Fetched through read_url's guarded fetch (every redirect hop checked, the
	connection pinned to the checked address), so neither a redirect nor a DNS
	rebind can point the renderer at an internal host."""
	from builder.ai.agent.tools.web import fetch_public

	try:
		response, _ = fetch_public(src)
	except Exception:
		return None
	content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
	if response.status_code >= 400 or not content_type.startswith("image/"):
		return None
	content = response.raw.read(MAX_IMAGE_BYTES + 1, decode_content=True)
	if len(content) > MAX_IMAGE_BYTES:
		return None
	return f"data:{content_type};base64,{base64.b64encode(content).decode()}"


def render_block_images(sources: dict[str, str]) -> list[dict] | None:
	"""All the block's pictures, or None if any one fails: a half-attached pair would
	leave the model unsure which variant it actually saw."""
	from builder.html_preview_image import render

	attachments = []
	for label, src in sources.items():
		try:
			image = render(image_view_html(src), width=1024, height=768)
		except Exception:
			logger.warning("read_page: image render failed for %s", src[:200], exc_info=True)
			return None
		data_url = "data:image/webp;base64," + base64.b64encode(image).decode()
		attachments.append({"caption": f"The block's {label}, on a grey backdrop:", "data_url": data_url})
	return attachments


def attach_block_images(ctx, block: dict) -> str:
	"""Render an image block's picture, and its dark-mode variant, for the model to
	look at. Goes through the page renderer, so SVG, data: and remote images work
	too. Returns a line for the read_page result saying what was attached."""
	from builder.ai.models import ModelRegistry

	attributes = block.get("attributes") or {}
	sources = {"image": attributes.get("src"), "dark-mode image": attributes.get("darkSrc")}
	sources = {label: src for label, src in sources.items() if src}
	if block.get("element") != "img" or not sources:
		return "This block has no image to show."
	if not ModelRegistry.supports_vision(ctx.loop_model):
		return "Your selected model can't view images."
	if ctx.image_views >= MAX_IMAGE_VIEWS_PER_TURN:
		return "Image view limit reached for this turn."
	sources = {label: renderable_source(src) for label, src in sources.items()}
	if None in sources.values():
		return "This image's address is private, internal or unreachable, so it can't be shown to you."
	ctx.image_views += 1
	attachments = render_block_images(sources)
	if attachments is None:
		return "The image could not be rendered; don't describe what you haven't seen."
	ctx.pending_images.extend(attachments)
	return f"Attached below: the block's {' and '.join(sources)}."


TOOLS = [preview_page]
