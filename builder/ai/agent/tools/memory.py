"""Durable agent memory — small facts Bob keeps across every chat on this site.

One Builder AI Memory doc = one self-contained fact (a brand detail, a standing
preference, a correction). The whole registry is injected into the agent's
context each turn (see AgentRunner.build_memory_context), so remembering is
write-only here: the model never needs a read tool."""

import frappe

from builder.ai.agent.registry import Tool

DOCTYPE = "Builder AI Memory"
MAX_MEMORIES = 50
MAX_FACT_CHARS = 500


def memory_context() -> str:
	"""The saved facts as a context block, one line per memory with its id (the
	handle `remember(forget=...)` takes). Empty string when nothing is saved."""
	rows = frappe.get_all(DOCTYPE, fields=["name", "content"], order_by="creation asc", limit=MAX_MEMORIES)
	if not rows:
		return ""
	lines = [f"- [{r.name}] {r.content}" for r in rows]
	return (
		"Saved memory — durable facts from past conversations on this site. "
		"Apply them without being asked; update stale ones with the remember tool:\n" + "\n".join(lines)
	)


def run_remember(ctx, args: dict) -> str:
	fact = (args.get("fact") or "").strip()
	forget = (args.get("forget") or "").strip()
	if not fact and not forget:
		return "FAILED: pass `fact` (to save) and/or `forget` (a memory id to delete)."
	parts = []
	if forget:
		parts.append(forget_memory(forget))
	if fact:
		parts.append(save_fact(fact))
	return " ".join(parts)


def forget_memory(memory_id: str) -> str:
	if not frappe.db.exists(DOCTYPE, memory_id):
		return f"FAILED: no memory '{memory_id}' — ids are in your Saved memory context."
	frappe.delete_doc(DOCTYPE, memory_id, ignore_permissions=True)
	return f"Forgot [{memory_id}]."


def save_fact(fact: str) -> str:
	if len(fact) > MAX_FACT_CHARS:
		return f"FAILED: keep a fact under {MAX_FACT_CHARS} characters — one self-contained sentence or two."
	if existing := frappe.db.get_value(DOCTYPE, {"content": fact}):
		return f"Already remembered as [{existing}]."
	if frappe.db.count(DOCTYPE) >= MAX_MEMORIES:
		return (
			f"FAILED: memory is full ({MAX_MEMORIES} facts). Forget an outdated one first "
			"(remember with forget=<id>)."
		)
	doc = frappe.get_doc({"doctype": DOCTYPE, "content": fact}).insert(ignore_permissions=True)
	return f"Remembered [{doc.name}]."


remember_tool = Tool(
	name="remember",
	side="server",
	description=(
		"Save a durable fact to your persistent memory, shared by every future chat on this site — "
		"or delete a stale one. Use it when the user states something that should outlive this "
		"conversation: the brand's name/story/voice, a standing preference ('always use metric', "
		"'never stock photos'), a correction to how you work. ONE short self-contained fact per call. "
		"Do NOT save one-off instructions, page-specific details, or anything the site's pages and "
		"design tokens already record."
	),
	parameters={
		"type": "object",
		"properties": {
			"fact": {
				"type": "string",
				"description": 'The fact to save, phrased to stand alone (e.g. "The owner\'s name is Meera; she prefers Hindi headings with English body text.").',
			},
			"forget": {
				"type": "string",
				"description": "Id of a saved memory to delete (from the Saved memory context). Pass together with `fact` to replace it.",
			},
		},
	},
	handler=run_remember,
)

TOOLS = [remember_tool]
