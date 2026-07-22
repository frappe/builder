import frappe
from frappe.model.document import Document
from frappe.utils.telemetry import capture


def capture_user_invited(doc: Document, method: str | None = None) -> None:
	if doc.app_name == "builder":
		capture("builder_user_invited", "builder")


def after_accept(invitation: Document, user: Document, user_inserted: bool) -> None:
	capture("builder_user_invitation_accepted", "builder")
