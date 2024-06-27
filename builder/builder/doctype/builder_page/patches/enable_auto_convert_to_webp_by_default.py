import frappe


def execute():
	frappe.db.set_value("Builder Settings", None, "auto_convert_images_to_webp", 1, update_modified=False)
