"""Confirm-gating for sensitive agent actions.

A sensitive tool NEVER mutates directly. It calls `request_confirmation`, which
persists a pending-action message and emits a clarify event carrying the payload,
then ends the turn (the tool is `side="terminal"`). The frontend renders an
Apply/Skip card; on Apply it calls the `confirm_pending_settings` endpoint, which
loads the stored payload and runs `apply_pending_action`. So every privileged write
(global settings, home page, new doctype, sample data, publish) is user-triggered —
the model can only *propose*.
"""

import frappe

from builder.ai.session import AISession

# Sensitive action kinds the confirm card understands. Kept explicit so an unknown
# kind can never be applied.
KINDS = {"home_page", "global_settings", "create_doctype", "seed_sample_data", "publish_site", "manage_pages"}

GLOBAL_SETTING_FIELDS = {"script", "style", "head_html", "body_html"}


def request_confirmation(ctx, kind: str, summary: str, payload: dict) -> None:
	"""Persist + emit a pending sensitive action, then end the turn without mutating."""
	message_id = AISession.try_append_message(
		ctx.session_id,
		"assistant",
		summary,
		message_type="clarification",
		task_type="agent",
		metadata={"status": "pending_action", "kind": kind, "payload": payload},
	)
	frappe.db.commit()
	ctx.emit(
		"clarify",
		question=summary,
		options=["Apply", "Skip"],
		pending_action={"kind": kind, "payload": payload},
		message_id=message_id,
	)


def apply_pending_action(kind: str, payload: dict) -> str:
	"""Run the real mutation for a confirmed action. Called ONLY from the confirm
	endpoint (user-triggered). Returns a short human summary of what happened."""
	if kind not in KINDS:
		frappe.throw(frappe._("Unknown pending action: {0}").format(kind))
	payload = payload or {}
	return {
		"home_page": apply_home_page,
		"global_settings": apply_global_settings,
		"create_doctype": apply_create_doctype,
		"seed_sample_data": apply_seed_sample_data,
		"publish_site": apply_publish_site,
		"manage_pages": apply_manage_pages,
	}[kind](payload)


def apply_home_page(payload: dict) -> str:
	route = (payload.get("route") or "").strip().lstrip("/")
	frappe.db.set_value("Builder Settings", None, "home_page", route)
	return frappe._("Home page set to /{0}").format(route)


def apply_global_settings(payload: dict) -> str:
	settings = frappe.get_single("Builder Settings")
	changed = []
	for field in GLOBAL_SETTING_FIELDS:
		if field in payload and payload[field] is not None:
			settings.set(field, payload[field])
			changed.append(field)
	if changed:
		settings.save(ignore_permissions=True)
	return frappe._("Updated global settings: {0}").format(", ".join(changed) or "nothing")


def apply_create_doctype(payload: dict) -> str:
	"""Create a Custom DocType (custom=1, created at runtime — no code files / app
	migration) with Guest read so public pages can query it."""
	name = (payload.get("name") or "").strip()
	if not name:
		frappe.throw(frappe._("Doctype name is required"))
	if frappe.db.exists("DocType", name):
		return frappe._("DocType {0} already exists").format(name)

	fields = []
	for f in payload.get("fields") or []:
		fieldname = (f.get("fieldname") or "").strip()
		if not fieldname:
			continue
		fields.append(
			{
				"fieldname": fieldname,
				"label": f.get("label") or fieldname.replace("_", " ").title(),
				"fieldtype": f.get("fieldtype") or "Data",
				"options": f.get("options"),
				"in_list_view": 1,
			}
		)
	if not fields:
		frappe.throw(frappe._("At least one field is required"))

	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": name,
			"module": "Builder",
			"custom": 1,
			"naming_rule": "Random",
			"fields": fields,
			"permissions": [
				{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
				# Public website pages read data as Guest.
				{"role": "Guest", "read": 1},
			],
		}
	).insert(ignore_permissions=True)
	return frappe._("Created DocType {0} with {1} field(s)").format(name, len(fields))


def apply_seed_sample_data(payload: dict) -> str:
	doctype = (payload.get("doctype") or "").strip()
	rows = payload.get("rows") or []
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(frappe._("DocType {0} does not exist").format(doctype))
	created = 0
	for row in rows:
		if not isinstance(row, dict):
			continue
		frappe.get_doc({"doctype": doctype, **row}).insert(ignore_permissions=True)
		created += 1
	return frappe._("Seeded {0} sample record(s) into {1}").format(created, doctype)


MANAGE_PAGE_ACTIONS = {"publish", "unpublish", "delete"}


def apply_manage_pages(payload: dict) -> str:
	"""Page lifecycle, user-confirmed: publish / unpublish / delete. Runs WITHOUT
	ignore_permissions — the confirming user's own rights decide."""
	action = (payload.get("action") or "").strip()
	if action not in MANAGE_PAGE_ACTIONS:
		frappe.throw(frappe._("Unknown page action: {0}").format(action))
	titles = []
	for page_id in payload.get("page_ids") or []:
		if not frappe.db.exists("Builder Page", page_id):
			continue
		doc = frappe.get_doc("Builder Page", page_id)
		titles.append(doc.page_title or page_id)
		if action == "delete":
			frappe.delete_doc("Builder Page", page_id)
		elif action == "unpublish":
			doc.unpublish()
		else:
			doc.publish()
	if not titles:
		frappe.throw(frappe._("No matching pages"))
	verb = {"publish": "Published", "unpublish": "Unpublished", "delete": "Deleted"}[action]
	return frappe._("{0} {1} page(s): {2}").format(verb, len(titles), ", ".join(titles))


def apply_publish_site(payload: dict) -> str:
	folder = (payload.get("folder") or "").strip()
	if not folder:
		frappe.throw(frappe._("Folder is required to publish a site"))
	pages = frappe.get_all("Builder Page", filters={"project_folder": folder}, pluck="name")
	published = 0
	for name in pages:
		doc = frappe.get_doc("Builder Page", name)
		doc.publish()
		published += 1
	frappe.db.set_value(
		"Builder Project Folder", folder, "generation_status", "Published", update_modified=False
	)
	return frappe._("Published {0} page(s)").format(published)
