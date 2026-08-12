import frappe

from builder.builder_analytics import setup_clicks_table


def execute():
	"""Click tracking became opt-in: `element` now holds the block id and `tag`/`href` were dropped.
	Old rows predate that schema, so reset the table and rebuild the DuckDB snapshot cleanly."""
	frappe.db.truncate("Builder Page Click")
	try:
		setup_clicks_table()
	except Exception:
		# DuckDB rebuild is best-effort; the periodic ingestion will recreate the table if needed.
		frappe.log_error("Failed to rebuild DuckDB clicks table after reset")
