import frappe


def execute():
	frappe.db.set_single_value("Builder Settings", "auto_convert_images_to_webp", 1, update_modified=False)
