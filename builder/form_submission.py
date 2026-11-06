import json
import re

import frappe
import requests
from frappe import _
from frappe.model import attachment_fieldtypes, no_value_fields
from frappe.utils import cstr, escape_html, strip_html, validate_email_address
from frappe.utils.password import decrypt, encrypt

MAX_VALUE_LENGTH = 5000
# what a visitor fills in, like a phone number or a choice, unlike a count
VISITOR_FIELDTYPES = {"Data", "Small Text", "Text", "Long Text", "Phone", "Select", "Autocomplete", "Check"}


def parse_destinations(destinations: str | None) -> list[dict]:
	try:
		parsed = json.loads(destinations or "[]")
	except ValueError:
		return []
	return [d for d in parsed if isinstance(d, dict)] if isinstance(parsed, list) else []


def seal_destinations(destinations: str, fieldnames: list[str]) -> str:
	"""Each destination is sealed with the form's own field names: the only values a
	visitor's submission may deliver to it."""
	sealed = [d | {"fields": fieldnames} for d in parse_destinations(destinations)]
	return encrypt(json.dumps(sealed))


def unseal_destinations(sealed: str) -> list[dict]:
	try:
		destinations = json.loads(decrypt(sealed))
	except (frappe.ValidationError, ValueError):
		# decrypt's message is about site_config, which means nothing to a visitor
		frappe.clear_messages()
		frappe.throw(_("This form can't be submitted."), frappe.PermissionError)
	return [d for d in destinations if isinstance(d, dict)] if isinstance(destinations, list) else []


def collect_form_doctypes(*blocks: str | list | None) -> set[str]:
	"""The DocTypes the forms in these block trees save their submissions to."""
	doctypes = set()
	for tree in blocks:
		# most pages have no form, so they skip the parse
		if isinstance(tree, str) and "data-send-to" not in tree:
			continue
		for block in walk_blocks(frappe.parse_json(tree) or []):
			for attributes in (block.get("attributes"), block.get("customAttributes")):
				doctypes |= get_destination_doctypes((attributes or {}).get("data-send-to"))
	return doctypes


def walk_blocks(blocks: list | dict):
	for block in blocks if isinstance(blocks, list) else [blocks]:
		if isinstance(block, dict):
			yield block
			yield from walk_blocks(block.get("children") or [])


def get_destination_doctypes(destinations: str | None) -> set[str]:
	doctypes = {
		cstr(d.get("value")).strip() for d in parse_destinations(destinations) if d.get("type") == "doctype"
	}
	return doctypes - {""}


def validate_new_form_doctypes(blocks: tuple, blocks_before: tuple):
	"""Check only the DocTypes these blocks newly save to, so editing a page someone else
	pointed at a DocType doesn't need that person's permissions."""
	for doctype in collect_form_doctypes(*blocks) - collect_form_doctypes(*blocks_before):
		validate_form_doctype(doctype)


def validate_form_doctype(doctype: str):
	# a guest's submission is saved with ignore_permissions, so only someone who can create
	# these records may hand that out
	if not is_form_doctype(doctype):
		frappe.throw(_("A form can't save its submissions to {0}").format(doctype))
	if not frappe.has_permission(doctype, "create"):
		frappe.throw(
			_("You need permission to create {0} records to save a form's submissions to it").format(doctype),
			frappe.PermissionError,
		)


def is_form_doctype(doctype: str) -> bool:
	if not frappe.db.exists("DocType", doctype):
		return False
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.is_virtual:
		return False
	# the framework's and Builder's own records (users, scripts, pages) are never a visitor's to create
	return bool(meta.custom) or frappe.get_doctype_app(doctype) not in ("frappe", "builder")


def list_form_doctypes() -> list[str]:
	"""The DocTypes this user may point a form at; is_form_doctype, as one query."""
	modules = frappe.get_all(
		"Module Def", filters={"app_name": ["not in", ["frappe", "builder"]]}, pluck="name"
	)
	names = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0, "is_virtual": 0},
		or_filters={"custom": 1, "module": ["in", modules or [""]]},
		pluck="name",
		order_by="name",
	)
	return [name for name in names if frappe.has_permission(name, "create")]


def list_form_doctype_fields(doctype: str) -> list[dict]:
	"""The fields a form can fill in this DocType. A `needed` one fails every submission
	that leaves it empty, and a `suggested` one is optional but a visitor's to fill in."""
	meta = frappe.get_meta(doctype)
	visitor_fields = get_visitor_fields(meta)
	needed = get_needed_fields(doctype, visitor_fields)
	return [
		{
			"fieldname": df.fieldname,
			"label": df.label or frappe.unscrub(df.fieldname),
			"fieldtype": df.fieldtype,
			"options": df.options,
			"needed": df.fieldname in needed,
			"suggested": df.fieldname not in needed and df.fieldname in visitor_fields,
		}
		for df in meta.fields
		if is_form_field(df) or df.fieldname in needed
	]


def get_visitor_fields(meta) -> set[str]:
	# a field in a hidden section or tab is the site's to fill, like the page a visitor came from
	fieldnames, hidden_tab, hidden_section = set(), False, False
	for df in meta.fields:
		if df.fieldtype == "Tab Break":
			hidden_tab, hidden_section = bool(df.hidden), False
		elif df.fieldtype == "Section Break":
			hidden_section = bool(df.hidden)
		elif not (hidden_tab or hidden_section) and is_visitor_field(df):
			fieldnames.add(df.fieldname)
	return fieldnames


def is_visitor_field(df) -> bool:
	# the site sets a read-only, fetched or restricted field itself, and a record's status
	if (
		df.read_only
		or df.hidden
		or df.fetch_from
		or df.permlevel
		or df.fieldname in ("status", "naming_series")
	):
		return False
	# a defaulted field is the site's too, but a checkbox's "0" is only its unticked state
	return df.fieldtype in VISITOR_FIELDTYPES and df.default in (None, "", "0")


def get_needed_fields(doctype: str, visitor_fields: set[str]) -> set[str]:
	# a new record has its defaults, so only the required fields still empty need the form
	doc = frappe.new_doc(doctype)
	needed = {fieldname for fieldname, _msg in doc._get_missing_mandatory_fields()}
	# a new record also picks a select's first option, but a required choice is still the visitor's
	needed |= {
		df.fieldname for df in doc.meta.get_select_fields() if df.reqd and df.fieldname in visitor_fields
	}
	# a record named after a field can't be saved without it, even if it isn't required
	if (doc.meta.autoname or "").startswith("field:") and not doc.get(doc.meta.autoname[6:]):
		needed.add(doc.meta.autoname[6:])
	return needed


class FormSubmission:
	"""A visitor's submission of a published form. Its destinations arrive sealed by the
	page render, so the visitor can neither read nor change where it is delivered."""

	def __init__(self, sealed_destinations: str, data: dict, path: str):
		self.destinations = unseal_destinations(sealed_destinations)
		fieldnames = {fieldname for d in self.destinations for fieldname in d.get("fields") or []}
		self.data = {key: cstr(value) for key, value in data.items() if key in fieldnames}
		self.path = path

	def deliver(self):
		self.check_lengths()
		# saved first, so a submission its DocType rejects isn't emailed or posted either
		for destination in self.destinations:
			if destination.get("type") == "doctype" and destination.get("value"):
				self.save(destination["value"], destination.get("fields") or [])
		if recipients := [e for e in self.get_destinations("email") if validate_email_address(e)]:
			self.send_email(recipients)
		for url in self.get_destinations("webhook"):
			frappe.enqueue(post_to_webhook, url=url, data=self.data, enqueue_after_commit=True)

	def check_lengths(self):
		# cutting a long answer short would lose its end without the visitor knowing
		for key, value in self.data.items():
			if len(value) > MAX_VALUE_LENGTH:
				message = _("This is {0} characters long, and can be at most {1}.").format(
					len(value), MAX_VALUE_LENGTH
				)
				frappe.response["invalid_field"] = {"name": key, "message": message}
				frappe.throw(message)

	def get_destinations(self, destination_type: str) -> list[str]:
		values = (
			cstr(d.get("value")).strip() for d in self.destinations if d.get("type") == destination_type
		)
		return [value for value in values if value]

	def save(self, doctype: str, fieldnames: list[str]):
		# checked again here, since an AI edit saves the page without its validation
		if not is_form_doctype(doctype):
			frappe.throw(_("This form can't be submitted."), frappe.PermissionError)
		meta = frappe.get_meta(doctype)
		doc = frappe.new_doc(doctype)
		for fieldname in fieldnames:
			df = meta.get_field(fieldname)
			if df and is_form_field(df):
				self.set_value(doc, df)
		try:
			doc.insert(ignore_permissions=True)
		except frappe.ValidationError:
			# the published form shows why on the input the visitor can fix
			frappe.response["invalid_field"] = self.get_invalid_field(doc, fieldnames)
			raise

	def set_value(self, doc, df):
		# a checkbox is only submitted when it is checked, whatever its value
		if df.fieldtype == "Check":
			doc.set(df.fieldname, int(df.fieldname in self.data))
		elif df.fieldname in self.data:
			doc.set(df.fieldname, self.data[df.fieldname])
		# a select left on its placeholder isn't submitted, and shouldn't keep the record's first option
		elif df.fieldtype == "Select" and not df.default:
			doc.set(df.fieldname, "")

	def get_invalid_field(self, doc, fieldnames: list[str]) -> dict | None:
		missing = [f for f, _msg in doc._get_missing_mandatory_fields() if f in fieldnames]
		if missing:
			label = _(doc.meta.get_label(missing[0]))
			return {"name": missing[0], "message": _("{0} is required").format(label)}
		message = strip_html(cstr(frappe.message_log[-1].get("message"))) if frappe.message_log else ""
		fields = [doc.meta.get_field(f) for f in fieldnames if doc.meta.has_field(f)]
		# a refused value's message names its field or label, or else quotes the value
		named = [df for df in fields if mentions(message, df.fieldname, df.label)]
		quoted = [df for df in fields if mentions(message, self.data.get(df.fieldname))]
		if named or quoted:
			return {"name": (named or quoted)[0].fieldname, "message": message.strip()}

	def send_email(self, recipients: list[str]):
		try:
			frappe.sendmail(
				recipients=recipients,
				subject=_("New form submission on {0}").format(self.path),
				message=self.get_message(),
			)
		except frappe.OutgoingEmailError:
			# the visitor can't fix the site's email setup, so the admin finds it in Error Log instead
			frappe.clear_messages()
			frappe.log_error(_("Form submission on {0} not emailed").format(self.path))

	def get_message(self) -> str:
		rows = "".join(
			f"<tr><td><b>{escape_html(key)}</b></td><td>{escape_html(value)}</td></tr>"
			for key, value in self.data.items()
		)
		return f"<table>{rows}</table>"


def mentions(message: str, *texts: str | None) -> bool:
	words = "|".join(re.escape(text) for text in texts if text and len(text) > 2)
	return bool(words and re.search(rf"(?<!\w)({words})(?!\w)", message, re.I))


def is_form_field(df) -> bool:
	return df.fieldtype not in no_value_fields and df.fieldtype not in attachment_fieldtypes


def post_to_webhook(url: str, data: dict):
	from builder.api import assert_not_private_url

	assert_not_private_url(url)
	requests.post(url, json=data, timeout=10).raise_for_status()
