import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	"""Builder Variable → Builder Token. Only the DocType and the label field are
	renamed — token doc names (the CSS `--<id>` handles) are untouched, so every
	existing page's var(--id) references keep resolving."""
	if not frappe.db.exists("DocType", "Builder Variable"):
		return
	if frappe.db.exists("DocType", "Builder Token"):
		merge_stale_builder_variables()
		return
	frappe.rename_doc("DocType", "Builder Variable", "Builder Token", force=True)
	frappe.reload_doc("builder", "doctype", "builder_token")
	rename_field("Builder Token", "variable_name", "token_name")


def merge_stale_builder_variables():
	"""Both doctypes exist when a site ran the rename and later re-synced the old
	model. Keep Builder Token, salvage rows only the old table has, drop the rest."""
	if frappe.db.table_exists("Builder Variable"):
		frappe.db.sql(
			"""INSERT INTO `tabBuilder Token`
				(name, creation, modified, modified_by, owner, docstatus,
				token_name, type, value, dark_value, is_standard, `group`)
			SELECT name, creation, modified, modified_by, owner, docstatus,
				variable_name, type, value, dark_value, is_standard, `group`
			FROM `tabBuilder Variable` bv
			WHERE NOT EXISTS (SELECT 1 FROM `tabBuilder Token` bt WHERE bt.name = bv.name)"""
		)
	frappe.delete_doc("DocType", "Builder Variable", ignore_missing=True, force=True)
	frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabBuilder Variable`")
