"""Stateless per-request tool context for the MCP server.

Reproduces the slice of AgentRunner that tool handlers touch (see
builder/ai/agent/loop.py) over the same server-authoritative lifecycle:
edits land on the WorkingTree, persist to draft_blocks, and mirror to any
open editor via the page-suffixed ai_chat_* realtime events. There is no
LLM loop here: the MCP client is both the model and the loop, so activity
and cancellation plumbing degrade to no-ops. A fresh context is built for
every request; the page is bound at construction, never focused.
"""

import frappe

from builder.ai import page_writer
from builder.ai.agent.tree import WorkingTree
from builder.ai.snapshots import capture_page_state, save_revert_snapshot

EVENT_PREFIX = "ai_chat"


def root_block_template() -> dict:
	"""The editor's fresh-page body template (frontend/src/utils/blockTemplate.ts
	case "body"), seeded for an empty page so add_block has a root to build under."""
	return {
		"blockId": "root",
		"element": "div",
		"originalElement": "body",
		"attributes": {},
		"baseStyles": {
			"display": "flex",
			"flexWrap": "wrap",
			"flexShrink": 0,
			"flexDirection": "column",
			"alignItems": "center",
		},
		"children": [],
	}


class McpCtx:
	session_id = None
	headless = True
	# No user canvas drives an MCP session, so guards keyed on the open page
	# correctly disable themselves.
	canvas_page_id = None

	def __init__(self, page_id: str | None = None):
		self.page_id = page_id
		self.tree: WorkingTree | None = None
		if page_id:
			root = page_writer.load_page_root(page_id)
			self.tree = WorkingTree(root or root_block_template())
		self.pending_client_ops: list[dict] = []
		# Pre-edit page state captured before a mutating call; flushed to a
		# Builder Snapshot on the first accepted edit (same revert semantics as
		# the in-app agent).
		self.pending_state: dict | None = None
		self.selected_block_ids: tuple = ()
		self.current_activity = None
		self.preview_count = 0
		self.pending_images: list[dict] = []
		self.loop_model = ""

	def page_root(self) -> dict | None:
		return self.tree.root if self.tree else None

	# --- revert snapshot ----------------------------------------------------

	def arm_snapshot(self) -> None:
		self.pending_state = capture_page_state(self.page_id)

	def ensure_revert_snapshot(self) -> None:
		if self.pending_state:
			save_revert_snapshot(self.page_id, self.pending_state)
			self.pending_state = None

	# --- realtime mirror ----------------------------------------------------

	def emit(self, suffix: str, after_commit: bool = False, **kwargs) -> None:
		"""Publish on the page's channel, the same events an open editor already
		listens to (frontend/src/components/ai/realtime.ts)."""
		if not self.page_id:
			return
		frappe.publish_realtime(
			f"{EVENT_PREFIX}_{suffix}_{self.page_id}",
			{"page_id": self.page_id, "session_id": None, **kwargs},
			after_commit=after_commit,
		)

	emit_page = emit

	# --- client ops ---------------------------------------------------------

	def queue_client_op(self, op: dict) -> None:
		self.pending_client_ops.append(op)

	def drain_queued_ops(self) -> list[dict]:
		"""Snapshot, sync the tree, mirror, and persist ops a handler queued
		(extract_component queues the rewritten page as set_page_blocks)."""
		ops, self.pending_client_ops = self.pending_client_ops, []
		if not ops:
			return []
		self.ensure_revert_snapshot()
		for op in ops:
			if op["tool_name"] == "set_page_blocks":
				self.tree.root = op["args"]["blocks"]
		self.emit("tool_batch", operations=ops)
		if self.page_id and self.tree and self.tree.root:
			page_writer.save_draft_blocks(self.page_id, self.tree.root)
		return ops

	def apply_block_op(self, tool_name: str, args: dict) -> str:
		"""Apply one block op to the authoritative tree; mirror and persist only
		when accepted, so a rejected op never reaches an open canvas."""
		content = self.tree.apply(tool_name, args)
		if not content.startswith("FAILED"):
			self.ensure_revert_snapshot()
			self.emit("tool_batch", operations=[{"tool_name": tool_name, "args": args}])
			if self.tree.root:
				page_writer.save_draft_blocks(self.page_id, self.tree.root)
		return content

	def mirror_page_root(self, root: dict) -> None:
		"""Replace an open editor's canvas wholesale (revert / copy design)."""
		self.tree = WorkingTree(root)
		self.emit("tool_batch", operations=[{"tool_name": "set_page_blocks", "args": {"blocks": root}}])

	# --- loop plumbing with no MCP equivalent -------------------------------

	def begin_activity(self, tool_name: str, args: dict) -> None:
		return None

	def end_activity(self, entry) -> None:
		return None

	def is_cancelled(self) -> bool:
		return False


class CaptureCtx(McpCtx):
	"""Runs a terminal (confirm-gated) handler for its validation only: with no
	session the pending message persist no-ops, and emit captures the proposed
	action instead of showing an Apply/Skip card."""

	def __init__(self, page_id: str | None = None):
		super().__init__(page_id)
		self.captured: dict | None = None

	def emit(self, suffix: str, after_commit: bool = False, **kwargs) -> None:
		if suffix == "clarify":
			self.captured = kwargs.get("pending_action")
