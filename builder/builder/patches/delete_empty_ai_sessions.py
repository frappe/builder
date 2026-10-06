import frappe


def execute():
	"""Opening the editor used to create a chat session, so most sessions never got a
	message. A session is now created by its first message; drop the empty ones."""
	spoken = set(frappe.get_all("Builder AI Message", distinct=True, pluck="session"))
	empty = [name for name in frappe.get_all("Builder AI Session", pluck="name") if name not in spoken]
	if empty:
		frappe.db.delete("Builder AI Session", {"name": ("in", empty)})
