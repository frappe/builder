# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Design tokens an extension defines.

A token styles every page the site publishes, so it belongs to the extension and
the site. Two people running one extension share its tokens.
"""

import frappe

from builder.extensions.access import assert_extension_access

TOKEN_DOCTYPE = "Builder Token"
TOKEN_TYPES = {"Color", "Dimension", "Font"}
TOKEN_FIELDS = ("token_name", "type", "value", "dark_value", "group")


@frappe.whitelist()
def set_extension_tokens(extension: str, tokens: list[dict]) -> None:
	"""Create or update a Builder Token per entry, keyed by (extension, key).

	`key` exists because Builder Token.name is a database-assigned uuid, so an
	extension has no other way to name the same token twice.

	Never deletes what a call leaves unmentioned. Dropping a token takes an
	explicit unset.
	"""
	assert_extension_access(extension, "token.write", writes=TOKEN_DOCTYPE)
	for token in frappe.parse_json(tokens):
		upsert_extension_token(extension, token)


@frappe.whitelist()
def unset_extension_token(extension: str, key: str) -> None:
	"""Delete one token this extension created.

	Quiet about a key that is not there: an extension dropping a palette it has
	already dropped is not an error, and the end state is the one it asked for.
	"""
	assert_extension_access(extension, "token.write", writes=TOKEN_DOCTYPE)
	name = find_extension_token(extension, key)
	if name:
		frappe.delete_doc(TOKEN_DOCTYPE, name)


def upsert_extension_token(extension: str, token: dict) -> None:
	key = (token.get("key") or "").strip()
	if not key:
		frappe.throw(frappe._("Every extension token needs a key."))
	if token.get("type") not in TOKEN_TYPES:
		frappe.throw(frappe._("A token type must be one of: {0}").format(", ".join(sorted(TOKEN_TYPES))))

	values = {field: token.get(field) for field in TOKEN_FIELDS if token.get(field) is not None}
	name = find_extension_token(extension, key)
	if name:
		frappe.get_doc(TOKEN_DOCTYPE, name).update(values).save()
		return

	frappe.get_doc({"doctype": TOKEN_DOCTYPE, "extension": extension, "key": key, **values}).insert()


def find_extension_token(extension: str, key: str) -> str | None:
	return frappe.db.get_value(TOKEN_DOCTYPE, {"extension": extension, "key": key}, "name")


def delete_extension_tokens(extension: str) -> None:
	"""Every token this extension defined.

	Only a development session calls this. A token an installed extension made
	outlives its user, because it styles pages the site serves.
	"""
	for token in frappe.get_all(TOKEN_DOCTYPE, filters={"extension": extension}, pluck="name"):
		frappe.delete_doc(TOKEN_DOCTYPE, token, ignore_permissions=True)
