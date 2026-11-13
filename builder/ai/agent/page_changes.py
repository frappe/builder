"""Changes Bob proposes for pages other than the one it is working on.

Edits to the working page apply live. An edit to any other page of the site is
checked against that page right away, so a bad ref comes straight back to the
model, but nothing is saved: it waits, with any new page Bob proposes, for the
end of the turn, where it all goes to the user as one confirm card. Apply replays
the checked ops on each page as it is THEN (apply_page_changes), so a page the user
changed meanwhile either takes the edit on top or is reported and left alone.
"""

import copy
import re

import frappe

from builder.ai import locks
from builder.ai.agent.edits import EditScript
from builder.ai.agent.selectors import walk_blocks
from builder.ai.agent.tree import WorkingTree, insert_child

# Change lines a page shows on the card before the rest fold into "+N more".
MAX_CHANGE_LINES = 6
MAX_NEW_PAGES = 5
APPLY_LOCK_TTL = 60

ASPECTS = {
	"inner_html": "text",
	"base_styles": "style",
	"tablet_styles": "tablet style",
	"mobile_styles": "mobile style",
	"attributes": "attributes",
	"element": "tag",
	"classes": "classes",
	"name": "name",
	"bind": "data binding",
	"props": "props",
	"client_script": "script",
}


def page_row(page_id: str) -> dict:
	row = frappe.db.get_value("Builder Page", page_id, ["page_title", "route"], as_dict=True) or {}
	return {
		"page_id": page_id,
		"title": row.get("page_title") or page_id,
		"route": route_path(row.get("route")),
	}


def route_path(route: str | None) -> str:
	return "/" + (route or "").strip().strip("/")


def block_label(block: dict) -> str:
	"""How the card names a block: its layer name, else a few words of its text."""
	if name := block.get("blockName"):
		return name
	text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", block.get("innerHTML") or "")).strip()
	if text:
		return f"“{text[:32]}…”" if len(text) > 32 else f"“{text}”"
	return f"a {block.get('element') or 'div'}"


def describe_ops(ops: list[dict], labels: dict[str, str]) -> list[str]:
	"""One plain line per change, for the card and the step that prepared it."""
	lines = []
	for op in ops:
		args = op["args"]
		label = labels.get(args.get("block_id")) or ""
		if op["tool_name"] == "add_block":
			lines.append(f"Add {block_label(args.get('block_json') or {})}")
		elif op["tool_name"] == "remove_block":
			lines.append(f"Remove {label}")
		elif op["tool_name"] == "move_block":
			lines.append(f"Move {label}")
		elif op["tool_name"] == "update_block":
			text = block_label({"innerHTML": args["inner_html"]}) if args.get("inner_html") else ""
			aspects = list(dict.fromkeys(ASPECTS[key] for key in args if key in ASPECTS))
			aspects = [aspect for aspect in aspects if not (text and aspect == "text")]
			line = f"Change {label}" + (f" to {text}" if text else "")
			lines.append(line + (f" ({', '.join(aspects)})" if aspects else ""))
	return list(dict.fromkeys(lines))


def summarise(lines: list[str]) -> list[str]:
	if len(lines) <= MAX_CHANGE_LINES:
		return lines
	rest = len(lines) - MAX_CHANGE_LINES + 1
	return [*lines[: MAX_CHANGE_LINES - 1], f"+{rest} more changes"]


class OtherPageEdit:
	"""One other page's edits this turn: its blocks as the edits leave them, and the
	ops that got them there, in order, ready to replay."""

	def __init__(self, page_id: str):
		from builder.ai.page_writer import load_page_root

		self.page = page_row(page_id)
		self.tree = WorkingTree(load_page_root(page_id))
		self.ops: list[dict] = []
		self.changes: list[str] = []

	def run(self, script: str, sets: dict) -> tuple[str, list[str]]:
		"""Check `script` against the page. A tool can write the database while
		applying (a component's definition takes an instance's script), so whatever
		it writes is rolled back: nothing here may land before the user says so."""
		labels = {b["blockId"]: block_label(b) for b, _ in walk_blocks(self.tree.root) if b.get("blockId")}
		frappe.db.savepoint("other_page_edit")
		try:
			content, accepted = EditScript(self.tree, sets).run(script)
		finally:
			frappe.db.rollback(save_point="other_page_edit")
		changes = describe_ops(accepted, labels)
		self.ops.extend(accepted)
		self.changes.extend(line for line in changes if line not in self.changes)
		return content, changes

	def payload(self) -> dict:
		return {**self.page, "changes": summarise(self.changes), "ops": self.ops}


class PageChanges:
	"""Everything a turn proposes outside its working page."""

	def __init__(self, folder: str | None = None):
		self.edits: dict[str, OtherPageEdit] = {}
		self.new_pages: list[dict] = []
		self.folder = folder or ""

	def __bool__(self) -> bool:
		return bool(self.new_pages or self.staged())

	def tree_of(self, page_id: str) -> WorkingTree | None:
		"""A page with edits this turn reads back as they leave it."""
		return edit.tree if (edit := self.edits.get(page_id)) else None

	def edit(self, page_id: str, script: str, sets: dict) -> tuple[str, list[str]]:
		edit = self.edits.get(page_id) or OtherPageEdit(page_id)
		if edit.tree.root is None:
			return (
				f"FAILED: '{edit.page['title']}' has no blocks yet, so there is nothing to edit. A page "
				"is built from the page itself: tell the user to open it and ask there.",
				[],
			)
		self.edits[page_id] = edit
		content, changes = edit.run(script, sets)
		if not changes:
			return content, changes
		content = content.replace("Applied", "Prepared", 1)
		return (
			f"{content}\nNOT APPLIED YET: these edits to '{edit.page['title']}' ({edit.page['route']}) "
			"wait for the user's OK, which they give on a card shown when your turn ends. Refs you "
			"just added work for more edits to this page this turn. Your reply says what you "
			"prepared for which page and that it applies once they confirm, never that it's done.",
			changes,
		)

	def propose_page(self, title: str, route: str, brief: str) -> str:
		title, brief = (title or "").strip(), (brief or "").strip()
		route = (route or "").strip().strip("/. ")
		if not title or not route:
			return "FAILED: a new page needs a title and a route."
		if len(self.new_pages) >= MAX_NEW_PAGES:
			return (
				f"FAILED: at most {MAX_NEW_PAGES} new pages per turn; propose the rest after these are built."
			)
		if taken := route_owner(route) or next((p for p in self.new_pages if p["route"] == route), None):
			owner = taken if isinstance(taken, str) else "another page you proposed"
			return f"FAILED: /{route} is already used by {owner}. Read the site's routes and pick a free one."
		self.new_pages.append({"title": title, "route": route, "brief": brief, "folder": self.folder})
		return (
			f"PROPOSED, NOT CREATED: '{title}' at /{route}. The user confirms it on a card when your turn "
			"ends; once they do, it is created and you build it in the next turn from this brief, so "
			"don't build it now and don't use generate_page for it. Your reply says what page you "
			"propose and that you'll build it once they confirm."
		)

	def payload(self) -> dict:
		return {
			"pages": [edit.payload() for edit in self.staged()],
			"new_pages": self.new_pages,
		}

	def reply(self) -> str:
		"""The turn's reply when the model wrote none."""
		names = [f"“{p['title']}”" for p in self.new_pages] + [f"“{e.page['title']}”" for e in self.staged()]
		return f"I've prepared changes to {', '.join(names)}. Check them below and apply when you're happy."

	def card_text(self) -> str:
		"""The card as text: what the model sees of it on later turns."""
		lines = ["Waiting for the user's OK:"]
		lines += [f"- New page “{p['title']}” at /{p['route']}. Brief: {p['brief']}" for p in self.new_pages]
		lines += [f"- “{e.page['title']}” ({e.page['route']}): {'; '.join(e.changes)}" for e in self.staged()]
		return "\n".join(lines)

	def staged(self) -> list[OtherPageEdit]:
		return [edit for edit in self.edits.values() if edit.ops]

	def dropped_note(self) -> str:
		if not self:
			return ""
		names = [f"“{p['title']}”" for p in self.new_pages] + [f"“{e.page['title']}”" for e in self.staged()]
		return f" The changes I prepared for {', '.join(names)} were not applied."


def route_owner(route: str) -> str | None:
	"""The title of the page serving `route`, if any."""
	bare = route.strip("/")
	row = frappe.db.get_value(
		"Builder Page", {"route": ("in", (bare, f"/{bare}"))}, ["page_title", "name"], as_dict=True
	)
	return (row.page_title or row.name) if row else None


def replay(tree: WorkingTree, ops: list[dict]) -> str:
	"""Re-apply checked ops to a page as it is now. Added blocks keep the ids they
	were checked with, so later ops that target them still land. Returns the first
	failure, "" when everything applied."""
	for op in ops:
		args = op["args"]
		if op["tool_name"] == "add_block" and args.get("block_json"):
			parent = tree.resolve(args.get("parent_block_id"))
			if parent is None:
				return "the block it adds into is gone"
			insert_child(
				parent, copy.deepcopy(args["block_json"]), args.get("after_block_id"), args.get("index")
			)
			continue
		result = tree.apply(op["tool_name"], copy.deepcopy(args))
		if result.startswith("FAILED") or "NOT FOUND" in result:
			return "a block it changes is gone"
	return ""


def apply_page_changes(payload: dict) -> tuple[str, list[dict]]:
	"""Apply a confirmed card: new pages first (an edit may link to one), then each
	page's edits. Every page succeeds or fails on its own. Returns the outcome line
	and one result per page for the chat to list."""
	results = [isolated(create_page, item, "create") for item in payload.get("new_pages") or []]
	results += [isolated(apply_page_edit, item, "edit") for item in payload.get("pages") or []]
	return outcome_text(results), results


def isolated(apply, item: dict, action: str) -> dict:
	"""One page's share of the card: a crash rolls back only that page and reads
	as its failure."""
	result = {
		"action": action,
		"page_id": item.get("page_id"),
		"title": item.get("title"),
		"route": route_path(item.get("route")),
	}
	frappe.db.savepoint("page_change")
	try:
		return {**result, **apply(item)}
	except frappe.PermissionError:
		reason = "you aren't permitted to create pages" if action == "create" else "you can't edit it"
	except frappe.ValidationError as e:
		reason = str(e) or "the page didn't validate"
	except Exception:
		frappe.log_error(f"Bob couldn't {action} a page", "builder.ai.page_changes")
		reason = "something went wrong"
	frappe.db.rollback(save_point="page_change")
	return {**result, "status": "failed", "detail": reason}


def create_page(item: dict) -> dict:
	route = (item.get("route") or "").strip().strip("/")
	if owner := route_owner(route):
		return {"status": "failed", "detail": f"/{route} was taken meanwhile by {owner}"}
	doc = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": item.get("title"),
			"route": route,
			"project_folder": item.get("folder") or "",
			"published": 0,
		}
	).insert()
	return {"page_id": doc.name, "status": "created", "brief": item.get("brief") or ""}


def apply_page_edit(item: dict) -> dict:
	from builder.ai.page_writer import load_page_root, save_draft_blocks
	from builder.ai.snapshots import capture_page_state, save_revert_snapshot

	page_id = item.get("page_id") or ""
	if not frappe.db.exists("Builder Page", page_id):
		return {"status": "failed", "detail": "the page was deleted"}
	if not frappe.has_permission("Builder Page", "write", doc=page_id):
		raise frappe.PermissionError
	with locks.guard(locks.page_key(page_id), APPLY_LOCK_TTL) as token:
		if not token:
			return {"status": "failed", "detail": "another AI task is editing it right now"}
		tree = WorkingTree(load_page_root(page_id))
		if failure := (replay(tree, item.get("ops") or []) if tree.root else "the page is empty now"):
			return {
				"status": "failed",
				"detail": f"it changed after I read it ({failure}). Ask me to try again",
			}
		save_revert_snapshot(page_id, capture_page_state(page_id))
		save_draft_blocks(page_id, tree.root)
	sync_open_editors(page_id, tree.root)
	return {"status": "changed", "detail": "; ".join(item.get("changes") or [])}


def sync_open_editors(page_id: str, root: dict) -> None:
	"""An editor with this page open mirrors it, so its autosave can't write its
	older copy back over the change."""
	from builder.ai.agent.loop import EVENT_PREFIX

	frappe.publish_realtime(
		f"{EVENT_PREFIX}_tool_batch_{page_id}",
		{"page_id": page_id, "operations": [{"tool_name": "set_page_blocks", "args": {"blocks": root}}]},
		user=frappe.session.user,
		after_commit=True,
	)


def outcome_text(results: list[dict]) -> str:
	lines = []
	for r in results:
		name = f"“{r['title']}” ({r['route']})"
		if r["status"] == "failed":
			verb = "create" if r["action"] == "create" else "change"
			lines.append(f"Couldn't {verb} {name}, so nothing was changed there: {r['detail']}.")
		else:
			lines.append(f"{'Created' if r['status'] == 'created' else 'Changed'} {name}.")
	return " ".join(lines) or "Nothing to apply."
