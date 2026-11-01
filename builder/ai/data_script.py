"""A read-only execution boundary for data scripts installed by Bob."""

import frappe

SCRIPT_PREFIX = "# builder:read-only\n"


def execute_readonly_script(script, local_values, filename):
	from builder.ai.agent.tools.python import scope_reads_to_user
	from builder.utils import get_safer_globals, safer_exec

	globals = get_safer_globals()
	globals["frappe"].pop("make_get_request", None)
	scope_reads_to_user(globals["frappe"])
	frappe.db.savepoint("builder_readonly_data")
	try:
		safer_exec(script, globals, local_values, script_filename=filename)
	finally:
		frappe.db.rollback(save_point="builder_readonly_data")
