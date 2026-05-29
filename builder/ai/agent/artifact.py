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

import logging

import frappe

from builder.ai import llm
from builder.ai.block_codec import BlockCodec
from builder.ai.prompts import Prompts
from builder.ai.session import AISession

logger = frappe.logger("builder.ai.agent.artifact")
logger.setLevel(logging.INFO)


def generate_page_yaml(ctx, args: dict) -> list[dict]:
	"""Stream a complete page of YAML on the heavy model, then return a
	`generate_page` client op carrying the authoritative full document.

	`ctx` is the AgentRunner. `args["brief"]` is the concise spec the
	conversational model assembled from the approved plan / conversation.
	Streams `kind="page_yaml"` chunks to the canvas as the model writes them.
	Returns [] if cancelled or the model produced nothing.
	"""
	brief = (args.get("brief") or "").strip()

	messages: list[dict] = [
		{"role": "system", "content": Prompts.GENERATION_YAML, "cache_control": {"type": "ephemeral"}},
	]
	# Prior conversation (incl. the approved plan) as proper role-tagged turns.
	messages.extend(AISession.build_context_messages_from_id(ctx.session_id))
	if brief:
		messages.append({"role": "user", "content": f"Build this page now:\n{brief}"})

	ctx.emit("progress", message="Building the page…")

	yaml_content = ""
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
		delta = chunk.choices[0].delta.content
		if delta:
			yaml_content += delta
			ctx.emit("stream", chunk=delta, kind="page_yaml")

	yaml_text = BlockCodec.strip_fences(yaml_content).strip()
	if not yaml_text:
		logger.warning("generate_page_yaml: model produced empty YAML")
		return []

	return [{"tool_name": "generate_page", "args": {"yaml": yaml_text}}]
