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
	"acquire_paid_asset",
	"activate_plugin",
	"home_page",
	"global_settings",
	"create_doctype",
	"seed_sample_data",
	"connect_form",
}

GLOBAL_SETTING_FIELDS = {"script", "style", "head_html", "body_html"}


def not_permitted(action: str) -> str:
	"""Declines a proposal the user couldn't apply, so Bob says so instead of raising a
	card whose Apply would fail."""
	return (
		f"DECLINED: this user isn't permitted to {action}, so no card was shown. Tell them in "
		"one plain sentence that someone with that permission (usually a System Manager) has "
		"to do it, then carry on with what you can do."
	)


def request_confirmation(ctx, kind: str, summary: str, payload: dict) -> None:
	"""Persist + emit a pending sensitive action, then end the turn without mutating."""
	metadata = {
		"runId": getattr(ctx, "run_id", None),
		"status": "pending_action",
		"kind": kind,
		"payload": payload,
	}
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
	endpoint (user-triggered), with the confirming user's own permissions, since the
	model wrote the payload. Returns a short human summary of what happened."""
	if kind not in KINDS:
		frappe.throw(frappe._("Unknown pending action: {0}").format(kind))
	payload = payload or {}
	from builder.ai.media import acquire_paid_asset
	from builder.plugins.bob import activate_candidate

	return {
		"activate_plugin": activate_candidate,
		"acquire_paid_asset": acquire_paid_asset,
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
	"""Create a Custom DocType (custom=1, no code files or migration). No Guest read:
	it would publish every field over the REST API; public pages use a data script."""
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
			],
		}
	).insert()
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
		frappe.get_doc({**row, "doctype": doctype}).insert()
		created += 1
	return frappe._("Seeded {0} sample record(s) into {1}").format(created, doctype)


def apply_connect_form(payload: dict) -> str:
	"""Wire a page form to real data: a private submission DocType + a guest-safe
	Web Form (the trusted, rate-limited, field-whitelisted boundary) + a client
	script that POSTs the form's fields to the Web Form's accept endpoint. Reused
	if the doctype/web form already exist. Returns the Desk link to the entries."""
	from builder.ai.agent.tools.forms import (
		desk_slug,
		is_builder_submission_doctype,
		missing_create_permission,
		normalize_fields,
	)

	doctype = (payload.get("doctype_name") or "").strip()
	fields = payload.get("fields") or []
	page_id = (payload.get("page_id") or "").strip()
	selector = (payload.get("form_selector") or "").strip()
	if not doctype or not fields or not selector or not page_id:
		frappe.throw(frappe._("connect_form needs a page, doctype, fields, and a form selector"))
	fields = normalize_fields(fields)
	frappe.get_doc("Builder Page", page_id).check_permission("write")
	if frappe.db.exists("DocType", doctype) and not is_builder_submission_doctype(doctype):
		frappe.throw(frappe._("{0} already exists and is not a form submission DocType").format(doctype))
	# Checked for both before creating either, so a missing permission leaves nothing half-made.
	if action := missing_create_permission(doctype):
		frappe.throw(frappe._("You are not permitted to {0}").format(action), frappe.PermissionError)
	wf_name = desk_slug(doctype)
	validate_form_reuse(doctype, wf_name, fields)

	# 1. private submission DocType — System Manager only, NO guest permission
	#    (the Web Form is the trusted boundary; submissions must not be readable by
	#    other guests).
	# Only DocType field keys (drop input_name, which is the browser-side name attr).
	doctype_fields = [
		{k: v for k, v in f.items() if k in ("fieldname", "label", "fieldtype", "options", "reqd")}
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
		).insert()

	# 2. Web Form bound to it — guest-allowed (login_required off), published.
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
					{k: f[k] for k in ("fieldname", "label", "fieldtype", "reqd")} for f in fields
				],
			}
		).insert(ignore_permissions=True)  # missing_create_permission above is the gate

	# 3. client script on the page: capture the form's fields and POST them to the
	#    stock Web Form accept endpoint (guest-safe, rate-limited, ignore_permissions).
	attach_form_script(page_id, doctype, wf_name, selector, fields)
	slug = desk_slug(doctype)
	return frappe._(
		"Form connected. Submissions save to '{0}'. View them in Desk: [/app/{1}](/app/{1})"
	).format(doctype, slug)


def validate_form_reuse(doctype: str, web_form: str, fields: list) -> None:
	"""Reject incompatible resources before schema creation can commit anything."""
	if frappe.db.exists("DocType", doctype):
		meta = frappe.get_meta(doctype)
		for field in fields:
			existing = meta.get_field(field["fieldname"])
			if (
				not existing
				or existing.fieldtype != field["fieldtype"]
				or bool(existing.reqd) != bool(field["reqd"])
			):
				frappe.throw(frappe._("The existing submission DocType has incompatible fields"))
		mapped = {f["fieldname"] for f in fields}
		if any(f.reqd and f.fieldname not in mapped and not f.default for f in meta.fields):
			frappe.throw(frappe._("The submission DocType requires fields absent from this form"))
	if not frappe.db.exists("Web Form", web_form):
		return
	doc = frappe.get_doc("Web Form", web_form)
	if doc.doc_type != doctype or not doc.published or doc.login_required or doc.get("key_required"):
		frappe.throw(frappe._("The existing Web Form is not a public endpoint for this submission DocType"))
	expected = {(f["fieldname"], f["fieldtype"], bool(f["reqd"])) for f in fields}
	actual = {(f.fieldname, f.fieldtype, bool(f.reqd)) for f in doc.web_form_fields}
	if expected != actual or not doc.allow_multiple:
		frappe.throw(frappe._("The existing Web Form has incompatible submission fields or settings"))


def attach_form_script(page_id: str, doctype: str, web_form: str, selector: str, fields: list) -> None:
	"""Create + attach a Builder Client Script that submits the form's inputs to
	the Web Form accept endpoint. Idempotent per (page, web_form, selector)."""
	from builder.ai.agent.tools.forms import form_script_name

	script_name = form_script_name(page_id, doctype, web_form, selector)
	existing = frappe.db.get_value("Builder Client Script", {"name": script_name}, "name")
	code = build_form_script(selector, web_form, fields)
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


def build_form_script(selector: str, web_form: str, fields: list) -> str:
	"""Wire exact HTML names to DocType fields, preserving native control semantics."""
	import json

	mappings = [{"fieldname": f, "input_name": f} if isinstance(f, str) else f for f in fields]
	sel, wf, fields_json = json.dumps(selector), json.dumps(web_form), json.dumps(mappings)
	return f"""// Auto-wired by Bob: submits through the Web Form accept endpoint.
(function () {{
  if (document.readyState === 'loading') {{ document.addEventListener('DOMContentLoaded', init); }}
  else {{ init(); }}
  function init() {{
    var SEL = {sel}, WF = {wf}, FIELDS = {fields_json};
    var form;
    try {{ form = document.querySelector(SEL); }} catch (e) {{ return; }}
    if (!form) return;
    if (form.tagName !== 'FORM' && form.querySelector('form')) form = form.querySelector('form');
    if (form.dataset.bobConnected) return;
    form.dataset.bobConnected = WF;
    var Q = 'input, select, textarea';
    var btn = form.querySelector('button[type="submit"], input[type="submit"], button:not([type])')
      || form.querySelector('button[type="button"]');
    var status = document.createElement('div');
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    form.appendChild(status);
    var busy = false;
    function fail(message) {{ status.textContent = message; return false; }}
    function valuesOf(controls) {{
      var values = [];
      controls.forEach(function (el) {{
        if ((el.type === 'checkbox' || el.type === 'radio') && !el.checked) return;
        if (el.tagName === 'SELECT') {{
          Array.prototype.forEach.call(el.selectedOptions, function (option) {{
            if (!option.disabled && !(option.parentElement.tagName === 'OPTGROUP' && option.parentElement.disabled)) {{
              values.push(option.value);
            }}
          }});
        }} else values.push(el.value);
      }});
      return values;
    }}
    function submit(e) {{
      if (e) e.preventDefault();
      if (busy) return false;
      var nativeForm = form.tagName === 'FORM';
      var inputs = Array.prototype.slice.call(nativeForm ? form.elements : form.querySelectorAll(Q));
      inputs = inputs.filter(function (el) {{
        return el.matches(Q) && ['submit', 'button', 'reset', 'image'].indexOf(el.type) === -1;
      }});
      if (nativeForm && !HTMLFormElement.prototype.reportValidity.call(form)) return false;
      if (!nativeForm && inputs.some(function (el) {{
        return el.reportValidity && !el.reportValidity();
      }})) return false;
      var data = Object.create(null);
      for (var i = 0; i < FIELDS.length; i++) {{
        var field = FIELDS[i];
        var named = inputs.filter(function (el) {{ return el.name === field.input_name; }});
        if (!named.length) return fail('This form is missing a configured field. Please contact the site owner.');
        var controls = named.filter(function (el) {{ return !el.matches(':disabled'); }});
        if (!controls.length) continue;
        if (controls.some(function (el) {{ return el.type === 'file'; }})) {{
          return fail('File uploads are not supported by this form.');
        }}
        var first = controls[0], value;
        var values = valuesOf(controls);
        if (field.reqd && (!values.length || values.every(function (v) {{ return v === ''; }}))) {{
          return fail('Please complete all required fields.');
        }}
        if (field.multiple) {{
          value = JSON.stringify(values);
        }} else if (first.type === 'checkbox' && field.fieldtype === 'Check' && controls.length === 1) {{
          value = first.checked ? 1 : 0;
        }} else {{
          if (first.multiple || values.length > 1 || (controls.length > 1 && first.type !== 'radio')) {{
            return fail('This form needs a multiple-value field mapping. Please contact the site owner.');
          }}
          if (!values.length) continue;
          value = values[0];
        }}
        data[field.fieldname] = value;
      }}
      if (!Object.keys(data).length) return false;
      busy = true;
      status.textContent = 'Sending…';
      var label = btn && btn.textContent;
      if (btn) {{ btn.textContent = 'Sending…'; btn.disabled = true; }}
      var headers = {{ 'Content-Type': 'application/json' }};
      var token = window.csrf_token || (window.frappe && window.frappe.csrf_token);
      if (token && token !== 'None') headers['X-Frappe-CSRF-Token'] = token;
      fetch('/api/method/frappe.website.doctype.web_form.web_form.accept', {{
        method: 'POST', headers: headers,
        body: JSON.stringify({{ web_form: WF, data: data }})
      }}).then(function (r) {{ if (!r.ok) throw r; return r.json(); }})
        .then(function (response) {{
          if (response.exc || response.exception) throw response;
          status.textContent = 'Thank you! Your submission was saved.';
          if (btn) btn.textContent = 'Thank you!';
          if (nativeForm) HTMLFormElement.prototype.reset.call(form);
        }})
        .catch(function () {{
          busy = false;
          status.textContent = 'Your submission could not be saved. Please try again.';
          if (btn) {{ btn.textContent = label || 'Try again'; btn.disabled = false; }}
        }});
      return false;
    }}
    if (form.tagName === 'FORM') {{
      form.addEventListener('submit', submit);
      if (btn && btn.type === 'button') btn.addEventListener('click', submit);
    }} else if (btn) btn.addEventListener('click', submit);
  }}
}})();
"""
