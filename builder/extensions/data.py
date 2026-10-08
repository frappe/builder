# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Methods that let an extension read and write documents.
Each method needs the `data.access` permission. Frappe then checks the permissions of the user.
So an extension gets only the documents that the user can get."""

import frappe
import frappe.client
from frappe import _

from builder.extensions.access import assert_extension_access

# The default rows for each call, and the maximum. Only the server keeps these limits.
DEFAULT_PAGE_LENGTH = 20
MAX_PAGE_LENGTH = 500


@frappe.whitelist()
def get_list(
	extension: str,
	doctype: str,
	fields: list[str] | None = None,
	filters: dict | list | None = None,
	or_filters: dict | list | None = None,
	order_by: str | None = None,
	group_by: str | None = None,
	limit_start: int = 0,
	limit_page_length: int = DEFAULT_PAGE_LENGTH,
) -> list[dict]:
	"""Returns one page of documents.
	`createListResource` sends `or_filters` and `group_by` on each fetch.
	If the method ignores a filter, it returns too many rows."""
	assert_extension_access(extension, "data.access")
	return frappe.client.get_list(
		doctype=doctype,
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		order_by=order_by,
		group_by=group_by,
		limit_start=limit_start,
		limit_page_length=get_page_length(limit_page_length),
	)


@frappe.whitelist()
def get_count(extension: str, doctype: str, filters: dict | list | None = None) -> int:
	"""Returns the number of matching documents.
	`reportview.get_count` reads all of `form_dict`, and fails on `extension`. So the call clears it.
	Do not use `frappe.db.count`. It does not apply user permissions."""
	assert_extension_access(extension, "data.access")

	sent = frappe.local.form_dict
	frappe.local.form_dict = frappe._dict()
	try:
		return frappe.client.get_count(doctype=doctype, filters=filters)
	finally:
		frappe.local.form_dict = sent


@frappe.whitelist()
def get_doc(extension: str, doctype: str, name: str) -> dict:
	"""Returns one document with its child tables."""
	assert_extension_access(extension, "data.access")
	return frappe.client.get(doctype=doctype, name=name)


@frappe.whitelist(methods=["POST"])
def insert_doc(extension: str, doctype: str, doc: dict | None = None) -> dict:
	"""Uses the doctype from the argument, not from the payload."""
	assert_extension_access(extension, "data.access")
	return frappe.client.insert({**(doc or {}), "doctype": doctype})


@frappe.whitelist(methods=["POST"])
def update_doc(extension: str, doctype: str, name: str, doc: dict | None = None) -> dict:
	"""Changes only the fields in `doc`. `set_value` does not change the standard fields."""
	assert_extension_access(extension, "data.access")
	return frappe.client.set_value(doctype, name, doc or {})


@frappe.whitelist(methods=["POST"])
def delete_doc(extension: str, doctype: str, name: str) -> None:
	assert_extension_access(extension, "data.access")
	frappe.client.delete(doctype, name)


def get_page_length(limit_page_length: int) -> int:
	"""Stops a call that asks for 0 rows or too many rows. Frappe reads 0 as all rows."""
	if not 1 <= limit_page_length <= MAX_PAGE_LENGTH:
		frappe.throw(_("Ask for 1 to {0} rows at a time.").format(MAX_PAGE_LENGTH))
	return limit_page_length
