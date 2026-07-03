import frappe


def execute():
	current_value = frappe.db.get_single_value(
		"Builder Settings",
		"execute_block_scripts_in_editor",
	)
	value = "Disable" if current_value in {"Don't Execute", "Disable"} else "Enable"
	frappe.db.set_value(
		"Builder Settings",
		None,
		"execute_block_scripts_in_editor",
		value,
		update_modified=False,
	)
