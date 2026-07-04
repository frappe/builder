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

from builder.ai import llm
from builder.ai.block_codec import BlockCodec
from builder.ai.models import ModelRegistry
from builder.ai.prompts import Prompts
from builder.ai.session import AISession

logger = frappe.logger("builder.ai.agent.artifact")
logger.setLevel(logging.INFO)

# Brief marker lines the design flow emits for images the generator should SEE
# (not just place): the user's reference and the chosen hero shot.
IMAGE_MARKER_RE = re.compile(r"(?:REFERENCE|HERO) IMAGE:\s*(\S+)", re.IGNORECASE)
MAX_ATTACHED_IMAGES = 2
MAX_IMAGE_BYTES = 3 * 1024 * 1024


def brief_image_parts(brief: str) -> list[dict]:
	"""Resolve the brief's image markers into message image parts. https URLs are
	attached directly (the provider fetches them); /files/ paths are read from the
	site and inlined as data URLs. The marker lines always stay in the brief text,
	so the model still knows the exact URLs to place in blocks."""
	parts = []
	for url in IMAGE_MARKER_RE.findall(brief or ""):
		if len(parts) >= MAX_ATTACHED_IMAGES:
			break
		if url.startswith("https://"):
			parts.append({"type": "image_url", "image_url": {"url": url}})
		elif url.startswith("/files/"):
			data_url = read_site_image(url)
			if data_url:
				parts.append({"type": "image_url", "image_url": {"url": data_url}})
	return parts


def read_site_image(file_url: str) -> str | None:
	try:
		name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not name:
			return None
		content = frappe.get_doc("File", name).get_content()
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


def log_generation_quality(model: str, finish_reason: str | None, yaml_text: str) -> None:
	"""Make the generation path debuggable: log model, finish_reason, YAML size, parse
	result, and top-level section count. A thin/broken page shows up here as a 'length'
	finish, a parse error, or very few sections — distinguishing a weak model from a
	pipeline bug."""
	import yaml as yaml_lib

	chars = len(yaml_text)
	sections = -1  # -1 = did not parse
	try:
		from builder.ai.page_writer import unwrap_root

		parsed = yaml_lib.safe_load(yaml_text)
		root = unwrap_root(parsed)
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
		{"role": "system", "content": Prompts.GENERATION_YAML, "cache_control": {"type": "ephemeral"}},
	]
	# Prior conversation (incl. the approved plan) as proper role-tagged turns.
	messages.extend(AISession.build_context_messages_from_id(ctx.session_id))
	# The approved wireframes (plan strip + chosen layout sketch) as plain SVG text.
	# Cards replay as text where svg degrades to '[sketch]', so without this the
	# generator never sees the composition the user actually approved.
	if svgs := AISession.collect_design_svgs(ctx.session_id):
		messages.append(
			{
				"role": "user",
				"content": "Approved wireframes (abstract layout sketches — match this composition and "
				"rhythm, not the literal shapes):\n" + "\n".join(svgs),
			}
		)
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
	stream = llm.complete(
		ctx.model,  # heavy model — generation quality
		messages,
		llm.TASK_PARAMS["complex"],
		stream=True,
		api_key=ctx.api_key,
	)
	for chunk in stream:
		if ctx.is_cancelled():
			try:
				stream.close()
			except Exception:
				pass
			from builder.ai.agent.loop import CancelledError

			raise CancelledError
		ctx.record_usage(chunk, model=ctx.model)  # generation streams on the heavy model
		if not chunk.choices:
			continue
		if fr := chunk.choices[0].finish_reason:
			finish_reason = fr
		delta = chunk.choices[0].delta.content
		if delta:
			yaml_content += delta
			if not ctx.headless:
				ctx.emit("stream", chunk=delta, kind="page_yaml")
			else:
				# Headless build: the chat has no canvas, but an editor opened on the
				# page IS one — stream the preview there so the user can click through
				# and watch the page assemble live ("Watch live" in the dashboard chat).
				ctx.emit_page("stream", chunk=delta, kind="page_yaml")

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
		logger.warning("generate_page_yaml: YAML produced no blocks (model=%s)", ctx.model)
		return []
	return [{"tool_name": "generate_page", "args": {"blocks": [root], "data_script": data_script}}]
