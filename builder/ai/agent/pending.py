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
KINDS = {
	"home_page",
	"global_settings",
	"create_doctype",
	"seed_sample_data",
	"publish_site",
	"manage_pages",
	"connect_form",
}

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
		"connect_form": apply_connect_form,
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


def apply_connect_form(payload: dict) -> str:
	"""Wire a page form to real data: a private submission DocType + a guest-safe
	Web Form (the trusted, rate-limited, field-whitelisted boundary) + a client
	script that POSTs the form's fields to the Web Form's accept endpoint. Reused
	if the doctype/web form already exist. Returns the Desk link to the entries."""
	from builder.ai.agent.tools.forms import desk_slug

	doctype = (payload.get("doctype_name") or "").strip()
	fields = payload.get("fields") or []
	page_id = (payload.get("page_id") or "").strip()
	selector = (payload.get("form_selector") or "").strip()
	if not doctype or not fields or not selector:
		frappe.throw(frappe._("connect_form needs a doctype, fields, and a form selector"))

	# 1. private submission DocType — System Manager only, NO guest permission
	#    (the Web Form is the trusted boundary; submissions must not be readable by
	#    other guests).
	if not frappe.db.exists("DocType", doctype):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": doctype,
				"module": "Builder",
				"custom": 1,
				"naming_rule": "Random",
				"fields": [{**f, "in_list_view": 1} for f in fields],
				"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
			}
		).insert(ignore_permissions=True)

	# 2. Web Form bound to it — guest-allowed (login_required off), published.
	wf_name = desk_slug(doctype)
	if not frappe.db.exists("Web Form", wf_name):
		frappe.get_doc(
			{
				"doctype": "Web Form",
				"name": wf_name,
				"title": doctype,
				"route": f"forms/{wf_name}",
				"doc_type": doctype,
				"module": "Builder",
				"published": 1,
				"login_required": 0,
				"allow_multiple": 1,
				"web_form_fields": [
					{"fieldname": f["fieldname"], "label": f["label"], "fieldtype": f["fieldtype"]}
					for f in fields
				],
			}
		).insert(ignore_permissions=True)

	# 3. client script on the page: capture the form's fields and POST them to the
	#    stock Web Form accept endpoint (guest-safe, rate-limited, ignore_permissions).
	if page_id and frappe.db.exists("Builder Page", page_id):
		attach_form_script(page_id, doctype, wf_name, selector, [f["fieldname"] for f in fields])

	frappe.db.commit()
	slug = desk_slug(doctype)
	return frappe._(
		"Form connected — submissions save to '{0}'. View them in Desk: [/app/{1}](/app/{1})"
	).format(doctype, slug)


def attach_form_script(page_id: str, doctype: str, web_form: str, selector: str, fieldnames: list) -> None:
	"""Create + attach a Builder Client Script that submits `selector`'s inputs to
	the Web Form accept endpoint. Idempotent per (page, web_form)."""
	script_name = f"Save {doctype} submissions"
	existing = frappe.db.get_value("Builder Client Script", {"name": script_name}, "name")
	code = build_form_script(selector, web_form, fieldnames)
	if existing:
		frappe.db.set_value("Builder Client Script", existing, "script", code, update_modified=False)
		script_id = existing
	else:
		script_id = (
			frappe.get_doc(
				{
					"doctype": "Builder Client Script",
					"name": script_name,
					"script_type": "JavaScript",
					"script": code,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	page = frappe.get_doc("Builder Page", page_id)
	if not any(r.builder_script == script_id for r in page.get("client_scripts") or []):
		page.append("client_scripts", {"builder_script": script_id})
		page.save(ignore_permissions=True)


def build_form_script(selector: str, web_form: str, fieldnames: list) -> str:
	"""The submit-wiring JS. Reads only the known fields (never a honeypot/extra),
	POSTs to the accept endpoint, and reflects success on the submit button."""
	import json

	sel = json.dumps(selector)
	wf = json.dumps(web_form)
	fields = json.dumps(fieldnames)
	return f"""// Auto-wired by Bob: saves this form to the '{web_form}' Web Form.
(function () {{
  var form = document.querySelector({sel});
  if (!form) return;
  var FIELDS = {fields};
  var btn = form.querySelector('button, [type="submit"], input[type="submit"]');
  var busy = false;
  function submit(e) {{
    if (e) e.preventDefault();
    if (busy) return false;
    var data = {{}};
    form.querySelectorAll('[name]').forEach(function (el) {{
      if (FIELDS.indexOf(el.name) !== -1 && el.value) data[el.name] = el.value;
    }});
    if (!Object.keys(data).length) return false;
    busy = true;
    var label = btn && btn.textContent;
    if (btn) {{ btn.textContent = 'Sending…'; btn.disabled = true; }}
    fetch('/api/method/frappe.website.doctype.web_form.web_form.accept', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ web_form: {wf}, data: data }})
    }}).then(function (r) {{ if (!r.ok) throw r; return r.json(); }})
      .then(function () {{
        if (btn) btn.textContent = 'Thank you!';
        form.querySelectorAll('[name]').forEach(function (el) {{ el.value = ''; }});
      }})
      .catch(function () {{
        busy = false;
        if (btn) {{ btn.textContent = label || 'Try again'; btn.disabled = false; }}
      }});
    return false;
  }}
  if (form.tagName === 'FORM') form.addEventListener('submit', submit);
  else if (btn) btn.addEventListener('click', submit);
}})();
"""
