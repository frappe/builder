"""Page-scoped design, verification and effect records, outside model transcripts."""

import hashlib
import json

import frappe

DOCTYPE = "Builder AI Artifact"


class Artifact:
	@staticmethod
	def key(page: str, kind: str, identity: str) -> str:
		return hashlib.sha256(f"{page}:{kind}:{identity}".encode()).hexdigest()[:32]

	@classmethod
	def save(
		cls,
		page: str,
		kind: str,
		payload: dict,
		*,
		identity: str | None = None,
		run: str | None = None,
		status="ready",
	):
		frappe.get_doc("Builder Page", page).check_permission("write")
		encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
		if len(encoded) > 2_000_000:
			raise ValueError("Artifact exceeds 2 MB; split it into smaller sections")
		name = cls.key(page, kind, identity or frappe.generate_hash(length=32))
		exists = frappe.db.exists(DOCTYPE, name)
		if exists:
			doc = frappe.get_doc(DOCTYPE, name, for_update=True)
		else:
			doc = frappe.get_doc({"doctype": DOCTYPE, "name": name, "page": page, "kind": kind})
		doc.update(
			{
				"payload_json": encoded,
				"run": run,
				"status": status,
				"label": str(payload.get("label") or kind)[:140],
			}
		)
		if exists:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True, set_name=name)
		return doc

	@staticmethod
	def get(name: str, page: str, kind: str | None = None):
		frappe.get_doc("Builder Page", page).check_permission("read")
		doc = frappe.get_doc(DOCTYPE, name)
		if (
			doc.kind in ("tool_result", "effect", "plugin")
			and doc.owner != frappe.session.user
			and "System Manager" not in frappe.get_roles()
		):
			raise frappe.PermissionError("This artifact belongs to another user's run")
		if doc.page != page or (kind and doc.kind != kind):
			raise ValueError("This artifact does not belong to the page or requested workflow")
		return doc, json.loads(doc.payload_json)

	@staticmethod
	def list(page: str, kind: str, limit=20):
		frappe.get_doc("Builder Page", page).check_permission("read")
		filters = {"page": page, "kind": kind}
		if kind in ("tool_result", "effect", "plugin") and "System Manager" not in frappe.get_roles():
			filters["owner"] = frappe.session.user
		return frappe.get_all(
			DOCTYPE,
			filters=filters,
			fields=["name", "label", "status", "modified", "payload_json"],
			order_by="creation desc",
			limit=min(limit, 50),
		)
