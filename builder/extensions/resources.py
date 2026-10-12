# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What an extension made, so no caller guesses ownership from a name.

These rows name the extension, not its installation. So they survive an
uninstall, because a doctype holds the site's data.

It also means a later installation owns what an earlier one made. An extension
can edit the doctype it created after it is installed again.
"""

import frappe

RESOURCE_DOCTYPE = "Builder Extension Resource"


def record_resource(extension: str, resource_type: str, resource_name: str) -> None:
	if find_resource(extension, resource_type, resource_name):
		return
	frappe.get_doc(
		{
			"doctype": RESOURCE_DOCTYPE,
			"extension": extension,
			"resource_type": resource_type,
			"resource_name": resource_name,
			"resource_created": get_resource_created(resource_type, resource_name),
		}
	).insert()


def forget_resource(extension: str, resource_type: str, resource_name: str) -> None:
	frappe.db.delete(
		RESOURCE_DOCTYPE,
		{"extension": extension, "resource_type": resource_type, "resource_name": resource_name},
	)


def find_resource(extension: str, resource_type: str, resource_name: str) -> str | None:
	"""The row only counts while the record it names is the one the extension made.

	Frappe runs no hook when a DocType is deleted, so a row can outlive its
	doctype. A new doctype with the same name has a new `creation`, so the old
	row no longer matches it.
	"""
	created = get_resource_created(resource_type, resource_name)
	if not created:
		return None
	return frappe.db.get_value(
		RESOURCE_DOCTYPE,
		{
			"extension": extension,
			"resource_type": resource_type,
			"resource_name": resource_name,
			"resource_created": created,
		},
		"name",
	)


def get_resource_created(resource_type: str, resource_name: str):
	return frappe.db.get_value(resource_type, resource_name, "creation")


def list_resources(extension: str, resource_type: str) -> list[str]:
	return frappe.get_all(
		RESOURCE_DOCTYPE,
		filters={"extension": extension, "resource_type": resource_type},
		pluck="resource_name",
	)


def follow_renamed_doctype(document, method, old: str, new: str, merge: bool = False) -> None:
	"""A rename keeps `creation`, so the row only needs the new name."""
	frappe.db.set_value(
		RESOURCE_DOCTYPE,
		{"resource_type": "DocType", "resource_name": old},
		"resource_name",
		new,
	)
