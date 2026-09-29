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
	"connect_form",
}

GLOBAL_SETTING_FIELDS = {"script", "style", "head_html", "body_html"}


def request_confirmation(ctx, kind: str, summary: str, payload: dict) -> None:
	"""Persist + emit a pending sensitive action, then end the turn without mutating."""
	metadata = {"status": "pending_action", "kind": kind, "payload": payload}
	# The card is this turn's ONLY persisted message — without the timeline and
	# trace, everything the turn did before proposing (a whole page build) is
	# invisible on reload and undebuggable after the fact.
	if timeline := ctx.timeline():
		metadata["steps"] = timeline
	if ctx.trace:
		metadata["debug"] = {"loopModel": ctx.loop_model, "trace": ctx.trace}
	message_id = AISession.try_append_message(
		ctx.session_id,
		"assistant",
		summary,
		message_type="clarification",
		task_type="agent",
		metadata=metadata,
	)
	ctx.emit(
		"clarify",
		question=summary,
		options=["Apply", "Skip"],
		pending_action={"kind": kind, "payload": payload},
		message_id=message_id,
		after_commit=True,
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
		"connect_form": apply_connect_form,
	}[kind](payload)


def apply_home_page(payload: dict) -> str:
	route = (payload.get("route") or "").strip().lstrip("/")
	frappe.db.set_single_value("Builder Settings", "home_page", route)
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
	# Only DocType field keys (drop input_name, which is the browser-side name attr).
	doctype_fields = [
		{k: v for k, v in f.items() if k in ("fieldname", "label", "fieldtype", "options")}
		| {"in_list_view": 1}
		for f in fields
	]
	if not frappe.db.exists("DocType", doctype):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": doctype,
				"module": "Builder",
				"custom": 1,
				"naming_rule": "Random",
				"fields": doctype_fields,
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
	#    Fieldnames in FORM ORDER — the script maps inputs positionally (preferring a
	#    matching name attr) so it works even if the form has no name attrs/class.
	if page_id and frappe.db.exists("Builder Page", page_id):
		ordered_fieldnames = [f["fieldname"] for f in fields]
		attach_form_script(page_id, doctype, wf_name, selector, ordered_fieldnames)
	slug = desk_slug(doctype)
	return frappe._(
		"Form connected. Submissions save to '{0}'. View them in Desk: [/app/{1}](/app/{1})"
	).format(doctype, slug)


def attach_form_script(page_id: str, doctype: str, web_form: str, selector: str, fieldnames: list) -> None:
	"""Create + attach a Builder Client Script that submits the form's inputs to
	the Web Form accept endpoint. Idempotent per (page, web_form)."""
	script_name = f"Save {doctype} submissions"
	existing = frappe.db.get_value("Builder Client Script", {"name": script_name}, "name")
	code = build_form_script(selector, web_form, fieldnames)
	if existing:
		# save(), NOT db.set_value — the doc's on_update regenerates the served
		# public .js file; a bare set_value leaves the page serving stale JS.
		doc = frappe.get_doc("Builder Client Script", existing)
		doc.script = code
		doc.save(ignore_permissions=True)
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
	"""The submit-wiring JS. `fieldnames` are the DocType fieldnames in FORM ORDER.
	It finds the form (the given selector, else auto-detects the container that best
	matches — has a submit control and roughly `fieldnames` many inputs), maps each
	input to a field POSITIONALLY (preferring a matching name attr), and POSTs to
	the stock accept endpoint. Robust to a form with no name attrs or class."""
	import json

	sel = json.dumps(selector or "")
	wf = json.dumps(web_form)
	fields = json.dumps(fieldnames)
	return f"""// Auto-wired by Bob: saves this form to the '{web_form}' Web Form.
(function () {{
  // The script loads in <head>, before the form is parsed — wait for the DOM.
  if (document.readyState === 'loading') {{ document.addEventListener('DOMContentLoaded', init); }}
  else {{ init(); }}
  function init() {{
  var SEL = {sel}, WF = {wf}, FIELDS = {fields};
  var Q = 'input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea';
  function findForm() {{
    if (SEL) {{ var f = document.querySelector(SEL); if (f && f.querySelector(Q)) return f; }}
    // Fallback: the tightest container that has a submit control and about the
    // expected number of inputs — the form even without a class hook.
    var best = null, bestScore = -1;
    document.querySelectorAll('form, section, div').forEach(function (c) {{
      var ins = c.querySelectorAll(Q);
      if (!ins.length || ins.length > 15) return;
      if (!c.querySelector('button, [type="submit"], [type="button"]')) return;
      var score = 100 - Math.abs(ins.length - FIELDS.length) * 20 - Math.min(c.querySelectorAll('*').length, 400) / 20;
      if (score > bestScore) {{ bestScore = score; best = c; }}
    }});
    return best;
  }}
  var form = findForm();
  if (!form) return;
  var inputs = Array.prototype.slice.call(form.querySelectorAll(Q));
  var btn = form.querySelector('button, [type="submit"], input[type="submit"], [type="button"]');
  var busy = false;
  function submit(e) {{
    if (e) e.preventDefault();
    if (busy) return false;
    var data = {{}};
    inputs.forEach(function (el, i) {{
      var fn = (el.name && FIELDS.indexOf(el.name) !== -1) ? el.name : FIELDS[i];
      if (fn && (el.value || '').trim()) data[fn] = el.value;
    }});
    if (!Object.keys(data).length) return false;
    busy = true;
    var label = btn && btn.textContent;
    if (btn) {{ btn.textContent = 'Sending…'; btn.disabled = true; }}
    fetch('/api/method/frappe.website.doctype.web_form.web_form.accept', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ web_form: WF, data: data }})
    }}).then(function (r) {{ if (!r.ok) throw r; return r.json(); }})
      .then(function () {{
        if (btn) btn.textContent = 'Thank you!';
        inputs.forEach(function (el) {{ el.value = ''; }});
      }})
      .catch(function () {{
        busy = false;
        if (btn) {{ btn.textContent = label || 'Try again'; btn.disabled = false; }}
      }});
    return false;
  }}
  // Attach to BOTH: the button click (fires whether or not it's type=submit) and,
  // for a real <form>, the submit event (Enter key). The busy flag dedupes.
  if (btn) btn.addEventListener('click', submit);
  if (form.tagName === 'FORM') form.addEventListener('submit', submit);
  }}
}})();
"""
