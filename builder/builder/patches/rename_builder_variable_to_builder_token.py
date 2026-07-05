import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	"""Builder Variable → Builder Token. Only the DocType and the label field are
	renamed — token doc names (the CSS `--<id>` handles) are untouched, so every
	existing page's var(--id) references keep resolving."""
	if not frappe.db.exists("DocType", "Builder Variable"):
		return
	frappe.rename_doc("DocType", "Builder Variable", "Builder Token", force=True)
	frappe.reload_doc("builder", "doctype", "builder_token")
	rename_field("Builder Token", "variable_name", "token_name")
