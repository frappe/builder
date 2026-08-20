"""Artifact generators — produce a large streamed artifact for a tool.

An *artifact tool* (one that sets `artifact=` on its `Tool`) delegates its
execution to a generator here. The generator runs on the user's selected *heavy*
model and streams the artifact to the client as plain content — reliable, unlike
tool-call argument streaming, which providers buffer (the canvas would stay
blank for the whole completion). After streaming, it returns the canonical
client op(s) for the loop to emit so the frontend applies the authoritative,
fully-parsed result.

The agent calling the tool is the only trigger: when the fast conversational
model decides to build the page, it calls `generate_page(brief=…)` and the loop
hands off here. No DB status or out-of-band heuristic gates generation.
"""

import base64
import logging
import re

import frappe
import requests

from builder.ai import llm
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.api import assert_not_private_url

logger = frappe.logger("builder.ai.agent.artifact")
logger.setLevel(logging.INFO)

# Brief marker lines the design flow emits for images the generator should SEE
# (not just place): the user's reference and the chosen hero shot.
IMAGE_MARKER_RE = re.compile(r"(?:REFERENCE|HERO) IMAGE:\s*(\S+)", re.IGNORECASE)
MAX_ATTACHED_IMAGES = 2
MAX_IMAGE_BYTES = 3 * 1024 * 1024
IMAGE_CHECK_TIMEOUT = 5


def image_url_resolves(url: str) -> bool:
	"""Whether the provider will be able to fetch this image.

	An attached URL is downloaded by the provider, and one it cannot reach fails
	the ENTIRE completion (OpenRouter: 400 "Error while downloading file. Upstream
	status code: 404"), which the user sees as "Something went wrong". Models
	retype these URLs out of search results and transpose digits, so a cheap HEAD
	is worth it before betting the turn on one.

	The URL comes out of a brief the model wrote, so it gets the same SSRF guard
	as any other fetch, and redirects are left for the provider to follow — a
	public URL that hops to an internal address must not be probed from here.
	A 3xx still counts as resolvable, since the provider will follow it.
	"""
	try:
		assert_not_private_url(url)
		r = requests.head(url, timeout=IMAGE_CHECK_TIMEOUT, allow_redirects=False)
		if r.status_code in (403, 405):  # some CDNs only answer GET
			r = requests.get(url, timeout=IMAGE_CHECK_TIMEOUT, stream=True, allow_redirects=False)
			r.close()
		return r.ok
	except Exception as e:
		logger.warning(f"brief image {url} unreachable: {e}")
		return False


def brief_image_parts(brief: str) -> list[dict]:
	"""Resolve the brief's image markers into message image parts. https URLs are
	attached directly (the provider fetches them); site file paths (public or
	private) are read from the site and inlined as data URLs. The marker lines always stay in the brief text,
	so the model still knows the exact URLs to place in blocks."""
	parts = []
	for url in IMAGE_MARKER_RE.findall(brief or ""):
		if len(parts) >= MAX_ATTACHED_IMAGES:
			break
		if url.startswith("https://"):
			if not image_url_resolves(url):
				logger.warning(f"skipping unreachable brief image: {url}")
				continue
			parts.append({"type": "image_url", "image_url": {"url": url}})
		elif url.startswith(("/files/", "/private/files/")):
			data_url = read_site_image(url)
			if data_url:
				parts.append({"type": "image_url", "image_url": {"url": data_url}})
	return parts


def read_site_image(file_url: str) -> str | None:
	try:
		name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not name:
			return None
		file = frappe.get_doc("File", name)
		# The path may come out of a model-written brief, so a private file is only
		# inlined when the user this run acts for may actually read it.
		if file.is_private and not file.has_permission("read"):
			logger.warning(f"read_site_image: {file_url} is private and not readable here")
			return None
		content = file.get_content()
		if isinstance(content, str):
			content = content.encode()
		if not content or len(content) > MAX_IMAGE_BYTES:
			return None
		ext = (file_url.rsplit(".", 1)[-1] or "png").lower()
		mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(ext)
		if not mime:
			return None
		return f"data:image/{mime};base64,{base64.b64encode(content).decode()}"
	except Exception as e:
		logger.warning(f"read_site_image failed for {file_url}: {e}")
		return None


def found_photo_list(ctx) -> str:
	"""The turn's search_images results, as an inventory the generator can draw on.

	Every url here came back from a provider, so it resolves — unlike one the model
	retyped from memory. Copy them EXACTLY."""
	found = getattr(ctx, "found_images", None) or []
	if not found:
		return ""
	preamble = (
		"PHOTOS AVAILABLE for this page — real results already searched for you. Use these "
		"EXACT urls in img src (copy character for character, never retype or guess one), and "
		"give every section that wants a photo one of them rather than falling back to a CSS "
		"composition. Unused ones are fine to ignore."
	)
	lines = [preamble]
	for i, p in enumerate(found, 1):
		desc = (p.get("description") or "").strip()[:100] or p.get("query") or "photo"
		lines.append(f"{i}. [{p.get('query')}] {desc} — {p.get('size')}\n   {p.get('url')}")
	return "\n".join(lines)


def reference_geometry(ctx) -> str:
	"""Geometry of every reference read this turn — the generator sees only the
	brief, and prose loses exactly these load-bearing values. The FIRST read is
	the page the agent was told to match (the user-named page or the home page),
	so it is labelled primary; unordered references let a stray sibling read
	restyle the build with the wrong design system."""
	reads = getattr(ctx, "reference_reads", None) or []
	if not reads:
		return ""
	preamble = (
		"REFERENCE PAGE GEOMETRY — pages of this site read this turn as references. When "
		"the brief asks this page to match them or sit in the same site, what follows is "
		"ground truth over any prose: reproduce the SAME root geometry (e.g. a shell row "
		"of rail component + scrolling main column) instead of defaulting to a plain "
		"vertical stack, and give each font the ROLE its usage shows — the dominant family "
		"is the working face for headings AND body; a font used once is a one-spot accent "
		"to reproduce in that one place (its element, its size), never the display face "
		"for every heading and never every section's opener — at most the hero moment. "
		"The reference's measured sizes beat this prompt's scale defaults: a calm "
		"reference stays calm."
	)
	if len(reads) == 1:
		return preamble + "\n\n" + reads[0]
	labelled = [
		f"PRIMARY REFERENCE — the page to match; where references disagree, THIS one is law:\n{reads[0]}"
	]
	labelled += [
		f"SECONDARY REFERENCE — background only, never the system to match:\n{read}" for read in reads[1:]
	]
	return preamble + "\n\n" + "\n\n".join(labelled)


def log_generation_quality(model: str, finish_reason: str | None, yaml_text: str) -> None:
	"""Make the generation path debuggable: log model, finish_reason, YAML size, parse
	result, and top-level section count. A thin/broken page shows up here as a 'length'
	finish, a parse error, or very few sections — distinguishing a weak model from a
	pipeline bug."""
	chars = len(yaml_text)
	sections = -1  # -1 = did not parse
	try:
		from builder.ai.page_writer import parse_generation_yaml, unwrap_root

		# The same salvaging parser persist_page uses — telemetry must agree with
		# what actually lands on the page (a salvaged parse is not a failed one).
		root = unwrap_root(parse_generation_yaml(yaml_text))
		if isinstance(root, dict):
			sections = len(root.get("c") or [])
	except Exception as e:
		logger.warning("generate_page: YAML did not parse (model=%s): %s", model, e)

	level = logging.WARNING if (finish_reason == "length" or sections in (-1, 0, 1)) else logging.INFO
	logger.log(
		level,
		"generate_page quality | model=%s finish_reason=%s yaml_chars=%d top_sections=%s",
		model,
		finish_reason,
		chars,
		sections,
	)
	if sections in (-1, 0):
		# A no-blocks generation costs a full retry — capture enough of the actual
		# output to diagnose WHAT didn't parse (bad quoting, prose preamble, …).
		logger.warning("generate_page unparsed head:\n%s", yaml_text[:800])
		logger.warning("generate_page unparsed tail:\n%s", yaml_text[-400:])


def stream_buffer_key(page_id: str) -> str:
	return f"builder_ai_page_stream:{page_id}"


def save_stream_buffer(ctx, yaml_content: str) -> None:
	"""Keep the in-flight generation stream in Redis so an editor that loads (or
	refreshes) mid-build can replay the preview instead of showing a stale draft."""
	frappe.cache().set_value(
		stream_buffer_key(ctx.page_id),
		frappe.as_json({"yaml": yaml_content, "session_id": ctx.session_id}),
		expires_in_sec=600,
	)


def clear_stream_buffer(page_id: str | None) -> None:
	if page_id:
		frappe.cache().delete_value(stream_buffer_key(page_id))


def generate_page_yaml(ctx, args: dict) -> list[dict]:
	"""Stream a complete page of YAML on the heavy model, persist it to the page
	(the server is authoritative), and return a `generate_page` client op carrying
	the expanded block tree — the canvas applies that, so both sides share block ids.

	`ctx` is the AgentRunner. `args["brief"]` is the concise spec the
	conversational model assembled from the approved plan / conversation.
	Streams `kind="page_yaml"` chunks to the canvas as the model writes them
	(live preview only — the returned op is the final word).
	Returns [] if the model produced nothing usable.
	"""
	brief = (args.get("brief") or "").strip()

	messages: list[dict] = [
		# 1h TTL: the generation system prompt is identical across every build on
		# the site, so it stays a cache read from one page build to the next.
		{
			"role": "system",
			"content": Prompts.GENERATION_YAML,
			"cache_control": {"type": "ephemeral", "ttl": "1h"},
		},
	]
	# Prior conversation (incl. the approved plan) as proper role-tagged turns, with
	# the newest attached images re-shown — a reference design pasted on an earlier
	# turn must reach the step that actually draws the page.
	messages.extend(
		AISession.build_context_messages_from_id(
			ctx.session_id, include_images=ModelRegistry.supports_vision(ctx.model)
		)
	)
	# The photos this turn actually found. Without them the generator can only use
	# urls the model retyped into the brief, which is why pages came back with one
	# photo or none: transcribing urls by hand is work, so it mostly didn't happen.
	if photos := found_photo_list(ctx):
		messages.append({"role": "user", "content": photos})
	# The geometry of reference pages read this turn — the brief alone cannot carry it.
	if geometry := reference_geometry(ctx):
		messages.append({"role": "user", "content": geometry})
	if brief:
		build_text = f"Build this page now:\n{brief}"
		# Vision models get the reference/hero images themselves, not just their
		# URLs: the user's attached image for THIS turn, plus the brief's marker
		# images. Text-only models keep working from the marker URLs.
		image_parts: list[dict] = []
		if ModelRegistry.supports_vision(ctx.model):
			if ctx.image_url:
				image_parts.append({"type": "image_url", "image_url": {"url": ctx.image_url}})
			image_parts.extend(brief_image_parts(brief))
		if image_parts:
			messages.append({"role": "user", "content": [{"type": "text", "text": build_text}, *image_parts]})
		else:
			messages.append({"role": "user", "content": build_text})

	ctx.emit("progress", message="Building the page…")

	yaml_content = ""
	finish_reason = None
	buffered_at = 0
	stream = llm.complete(
		ctx.model,  # heavy model — generation quality
		messages,
		llm.TASK_PARAMS["complex"],
		stream=True,
		api_key=ctx.api_key,
	)
	try:
		for chunk in stream:
			if ctx.is_cancelled():
				# Stop, but KEEP: what already streamed is paid-for, visible work.
				# Fall through to persist the partial page; the loop's own cancel
				# check ends the turn right after this step returns.
				try:
					stream.close()
				except Exception:
					pass
				logger.info("generate_page_yaml: cancelled mid-stream, keeping the partial page")
				break
			ctx.record_usage(chunk, model=ctx.model)  # generation streams on the heavy model
			if not chunk.choices:
				continue
			if fr := chunk.choices[0].finish_reason:
				finish_reason = fr
			delta = chunk.choices[0].delta.content
			if delta:
				# offset = position of this chunk in the full stream, so a client that
				# replayed the buffer (mid-build refresh) can drop duplicates / detect gaps.
				offset = len(yaml_content)
				yaml_content += delta
				ctx.emit("stream", chunk=delta, kind="page_yaml", offset=offset)
				if len(yaml_content) - buffered_at >= 512:
					buffered_at = len(yaml_content)
					save_stream_buffer(ctx, yaml_content)
	finally:
		# The buffer only serves mid-build refreshes; once this function returns the
		# draft is persisted (or the turn failed/cancelled) and the DB is the truth.
		clear_stream_buffer(ctx.page_id)

	yaml_text = BlockCodec.strip_fences(yaml_content)
	# Generation was a blind spot — log enough to explain a thin/broken/truncated page:
	# the model, finish_reason (="length" → ran out of tokens mid-page), the YAML size,
	# whether it parses, and how many top-level sections (root.c) it actually produced.
	log_generation_quality(ctx.model, finish_reason, yaml_text)
	if not yaml_text or not ctx.page_id:
		logger.warning("generate_page_yaml: nothing to persist (model=%s, page=%s)", ctx.model, ctx.page_id)
		return []

	from builder.ai import page_writer

	root, data_script = page_writer.persist_page(ctx.page_id, yaml_text)
	if root is None:
		# A discarded generation is paid-for work — keep the raw text for diagnosis
		# (the parse error itself is logged by parse_generation_yaml with line info).
		dump = frappe.get_site_path("private", "files", f"ai-failed-generation-{ctx.page_id}.yaml")
		try:
			with open(dump, "w") as f:  # nosemgrep
				f.write(yaml_text)
		except OSError:
			dump = "<unwritable>"
		logger.warning(
			"generate_page_yaml: YAML produced no blocks (model=%s), raw saved to %s", ctx.model, dump
		)
		return []
	return [{"tool_name": "generate_page", "args": {"blocks": [root], "data_script": data_script}}]
