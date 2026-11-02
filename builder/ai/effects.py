"""Canonical mutation receipts and conflict-aware undo, committed with each effect."""

import copy
import json
from contextvars import ContextVar

import frappe

from builder.ai.artifacts import Artifact
from builder.ai.revisions import PAGE_FIELDS, digest, page_revision, require_revision

ACTIVE_EFFECT = ContextVar("builder_ai_effect", default=None)
FIELDS = {
	"Builder Page": (*PAGE_FIELDS, "client_scripts", "ai_project"),
	"Builder AI Project": ("title", "brief", "tasks_json", "revision"),
	"Builder Component": ("block", "component_name", "component_data_script"),
	"Builder Client Script": ("script", "script_type"),
	"Builder Token": ("token_name", "type", "value", "dark_value", "group"),
}


def document_state(doc):
	values = {key: doc.get(key) for key in FIELDS[doc.doctype]}
	if doc.doctype == "Builder Page":
		values["client_scripts"] = [
			{"builder_script": row.builder_script} for row in doc.get("client_scripts") or []
		]
	return copy.deepcopy(values)


def capture_document(doc, method=None):
	if recorder := ACTIVE_EFFECT.get():
		recorder.capture(doc)


class EffectReceipt:
	def __init__(self, ctx, op):
		self.ctx, self.op = ctx, copy.deepcopy(op)
		self.identity = f"{ctx.run_id}:{ctx.current_tool_call}"
		self.records = {}
		self.token = None

	def replay(self):
		name = Artifact.key(self.ctx.page_id, "effect", self.identity)
		if not frappe.db.exists("Builder AI Artifact", name):
			return None
		_, value = Artifact.get(name, self.ctx.page_id, "effect")
		if value["request"] != digest(self.op):
			raise ValueError("A tool delivery reused its identifier with different arguments")
		return value

	def begin(self, lock=True):
		from builder.ai.runs import AIRun

		run = frappe.get_doc(AIRun.DOCTYPE, self.ctx.run_id, for_update=True)
		if run.status != "running" or run.cancel_requested or run.run_user != frappe.session.user:
			raise ValueError("This run no longer owns the change. Reload the page before continuing.")
		if lock:
			require_revision(self.ctx.page_id, self.ctx.expected_revision)
		self.capture(frappe.get_doc("Builder Page", self.ctx.page_id))
		self.token = ACTIVE_EFFECT.set(self)

	def capture(self, doc):
		if doc.doctype not in FIELDS or any(
			entry["doc"] is doc
			or (doc.name and entry["doc"].doctype == doc.doctype and entry["doc"].name == doc.name)
			for entry in self.records.values()
		):
			return
		key = (doc.doctype, doc.name) if doc.name else id(doc)
		if key in self.records:
			return
		if len(self.records) >= 100:
			raise ValueError("This change touches too many documents. Split it into smaller steps.")
		before = None
		if not doc.is_new() and doc.name and frappe.db.exists(doc.doctype, doc.name):
			before = document_state(frappe.get_doc(doc.doctype, doc.name))
		self.records[key] = {"doc": doc, "before": before}

	def close(self):
		if self.token is not None:
			ACTIVE_EFFECT.reset(self.token)
			self.token = None

	def finish(self, result, operations):
		self.close()
		changes = []
		for entry in self.records.values():
			doc = entry["doc"]
			after = (
				document_state(frappe.get_doc(doc.doctype, doc.name))
				if frappe.db.exists(doc.doctype, doc.name)
				else None
			)
			if entry["before"] != after:
				changes.append(
					{"doctype": doc.doctype, "name": doc.name, "before": entry["before"], "after": after}
				)
		value = {
			"request": digest(self.op),
			"tool": self.op["tool_name"],
			"changes": changes,
			"result": result,
			"operations": operations,
		}
		Artifact.save(self.ctx.page_id, "effect", value, identity=self.identity, run=self.ctx.run_id)
		self.ctx.expected_revision = page_revision(self.ctx.page_id)
		return changes


def run_changes(run_ids):
	rows = frappe.get_all(
		"Builder AI Artifact",
		filters={"kind": "effect", "run": ["in", run_ids]},
		fields=["payload_json"],
		order_by="creation asc",
	)
	changes = {}
	for row in rows:
		for change in json.loads(row.payload_json).get("changes", []):
			key = (change["doctype"], change["name"])
			if key not in changes:
				changes[key] = change
			else:
				changes[key]["after"] = change["after"]
	return list(changes.values())


def restore_effects(run_ids):
	changes = run_changes(run_ids)
	# Validate every target before restoring any; never undo someone else's later edit.
	for change in sorted(changes, key=lambda c: (c["doctype"], c["name"])):
		doc = frappe.get_doc(change["doctype"], change["name"], for_update=True)
		doc.check_permission("write" if change["before"] else "delete")
		if document_state(doc) != change["after"]:
			raise ValueError(f"{doc.doctype} {doc.name} changed since Bob's edit. Nothing was reverted.")
	# Remove new links before deleting a newly-created shared document.
	for change in sorted(changes, key=lambda c: (c["before"] is None, c["doctype"] != "Builder Page")):
		if change["before"] is None:
			frappe.delete_doc(change["doctype"], change["name"])
		else:
			doc = frappe.get_doc(change["doctype"], change["name"])
			doc.update(change["before"])
			doc.save()
	return bool(changes)
