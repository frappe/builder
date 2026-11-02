"""Private user/page/project memory; site-wide facts require explicit administrator scope."""

import frappe

DOCTYPE = "Builder AI Memory"


def permission_query(user=None):
	user = frappe.db.escape(user or frappe.session.user)
	return f"(`tab{DOCTYPE}`.scope='site' OR `tab{DOCTYPE}`.memory_user={user} OR (COALESCE(`tab{DOCTYPE}`.memory_user,'')='' AND `tab{DOCTYPE}`.owner={user}))"


def has_permission(doc, user=None, permission_type=None, **kwargs):
	user = user or frappe.session.user
	if doc.scope == "site":
		return permission_type == "read" or "System Manager" in frappe.get_roles(user)
	return (doc.memory_user or doc.owner) == user


def validate(doc):
	if doc.is_new():
		doc.memory_user = frappe.session.user
		doc.scope = doc.scope or "user"
	elif not has_permission(doc, permission_type="write"):
		raise frappe.PermissionError("This memory belongs to another user")
	if doc.scope == "site" and "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError("Only a System Manager may set site-wide memory")
	if doc.scope == "page":
		frappe.get_doc("Builder Page", doc.page).check_permission("write")
	if doc.scope == "project":
		frappe.get_doc("Builder AI Project", doc.project).check_permission("write")
	if len(doc.content or "") > 500:
		raise ValueError("Keep a memory under 500 characters")


def visible(page_id=None):
	project = frappe.db.get_value("Builder Page", page_id, "ai_project") if page_id else None
	rows = frappe.get_list(
		DOCTYPE,
		fields=["name", "content", "scope", "page", "project"],
		order_by="modified desc",
		limit_page_length=200,
	)
	return [
		row
		for row in rows
		if row.scope in (None, "", "user", "site")
		or (row.scope == "page" and row.page == page_id)
		or (row.scope == "project" and project and row.project == project)
	][:50]
