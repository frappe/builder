"""A record of every document an AI turn writes, so reverting the turn puts all of it back.

While a turn runs, doc events record each document the first time the turn saves,
inserts or deletes it: its state before, or that the turn created it. Raw column
writes skip doc events, so they call `touch` first. Reverting a turn undoes its
entries and every later turn's, newest first."""

import json

import frappe

DOCTYPE = "Builder AI Change"
SAVEPOINT = "builder_ai_revert"

# The turn's own bookkeeping; undoing it would erase the chat, component versions or logs.
UNRECORDED_DOCTYPES = frozenset(
	{
		DOCTYPE,
		"Builder AI Session",
		"Builder AI Message",
		"Builder Snapshot",
		"Version",
		"Comment",
		"Error Log",
		"Deleted Document",
		"Activity Log",
		"File",
	}
)
BOOKKEEPING_FIELDS = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"idx",
		"docstatus",
		"doctype",
		"parent",
		"parenttype",
		"parentfield",
		"_user_tags",
		"_comments",
		"_assign",
		"_liked_by",
		"_seen",
	}
)


class TurnJournal:
	def __init__(self, session_id: str):
		self.session_id = session_id
		self.entries: dict[tuple[str, str], str] = {}
		self.updated: set[tuple[str, str]] = set()

	@staticmethod
	def active() -> "TurnJournal | None":
		return frappe.flags.get("builder_ai_journal")

	def __enter__(self) -> "TurnJournal":
		frappe.flags.builder_ai_journal = self
		return self

	def __exit__(self, *exc) -> None:
		frappe.flags.builder_ai_journal = None
		try:
			self.record_after_images()
		except Exception:
			frappe.logger("builder.ai.journal").warning("Could not record after-images", exc_info=True)

	def record(self, doctype: str, name: str, action: str, before: dict | None = None) -> None:
		if (doctype, name) in self.entries or doctype in UNRECORDED_DOCTYPES:
			return
		entry = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"session": self.session_id,
				"reference_doctype": doctype,
				"reference_name": name,
				"action": action,
				"before": frappe.as_json(before) if before else None,
			}
		).insert(ignore_permissions=True)
		self.entries[(doctype, name)] = entry.name
		if action == "Update":
			self.updated.add((doctype, name))

	def record_after_images(self) -> None:
		"""How the turn left each document it updated, so a revert restores only the fields it changed."""
		for doctype, name in self.updated:
			if exists(doctype, name):
				after = frappe.as_json(frappe.get_doc(doctype, name).as_dict())
				frappe.db.set_value(
					DOCTYPE, self.entries[(doctype, name)], "after", after, update_modified=False
				)


def record_insert(doc, method=None) -> None:
	if (journal := TurnJournal.active()) and not doc.meta.istable:
		journal.record(doc.doctype, doc.name, "Insert")


def record_update(doc, method=None) -> None:
	journal = TurnJournal.active()
	before = doc.get_doc_before_save() if journal else None
	if before is not None and not doc.meta.istable:
		journal.record(doc.doctype, doc.name, "Update", before.as_dict())


def record_delete(doc, method=None) -> None:
	if (journal := TurnJournal.active()) and not doc.meta.istable:
		journal.record(doc.doctype, doc.name, "Delete", doc.as_dict())


def touch(doctype: str, name: str) -> None:
	"""Record a document before a raw column write, which skips the doc events that would."""
	journal = TurnJournal.active()
	if journal and (doctype, name) not in journal.entries and exists(doctype, name):
		journal.record(doctype, name, "Update", frappe.get_doc(doctype, name).as_dict())


def revert_since(session_id: str, since) -> list[str]:
	"""Undo the session's recorded changes from `since` on and return what could not be undone.
	Restores run newest first, then deletions of created documents, newest first, so nothing is
	deleted while a restored document still links to it."""
	entries = frappe.get_all(
		DOCTYPE,
		filters={"session": session_id, "creation": (">=", since)},
		fields=["name", "reference_doctype", "reference_name", "action", "before", "after"],
		order_by="creation desc",
	)
	failures = []
	for entry in sorted(entries, key=lambda entry: entry.action == "Insert"):
		frappe.db.savepoint(SAVEPOINT)
		try:
			undo(entry)
		except Exception as e:
			rollback_to_savepoint()
			failures.append(f"{entry.reference_doctype} {entry.reference_name}: {e}")
	if entries:
		frappe.db.delete(DOCTYPE, {"name": ("in", [entry.name for entry in entries])})
	return failures


def undo(entry) -> None:
	doctype, name = entry.reference_doctype, entry.reference_name
	if entry.action == "Insert":
		if exists(doctype, name):
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		return
	before = json.loads(entry.before)
	if not exists(doctype, name):
		frappe.get_doc(before).insert(ignore_permissions=True, set_name=name)
		return
	doc = frappe.get_doc(doctype, name)
	for field in changed_fields(before, json.loads(entry.after) if entry.after else None):
		doc.set(field, without_bookkeeping(before[field]))
	doc.save(ignore_permissions=True)


def changed_fields(before: dict, after: dict | None) -> list[str]:
	fields = [field for field in before if field not in BOOKKEEPING_FIELDS and not field.startswith("__")]
	if after is None:
		return fields
	return [field for field in fields if comparable(before[field]) != comparable(after.get(field))]


def without_bookkeeping(value):
	if not isinstance(value, list):
		return value
	return [
		{key: v for key, v in row.items() if key not in BOOKKEEPING_FIELDS} if isinstance(row, dict) else row
		for row in value
	]


def comparable(value) -> str:
	return frappe.as_json(without_bookkeeping(value))


def exists(doctype: str, name: str) -> bool:
	if not frappe.db.exists("DocType", doctype):
		return False
	return bool(frappe.get_meta(doctype).issingle or frappe.db.exists(doctype, name))


def rollback_to_savepoint() -> None:
	# DDL (deleting a DocType drops its table) commits implicitly, which discards the savepoint.
	try:
		frappe.db.rollback(save_point=SAVEPOINT)
	except Exception:
		pass
