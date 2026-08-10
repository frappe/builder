import frappe

# Block fields moved from JSON to Long Text because MariaDB's json_valid
# rejects trees nested deeper than 32 levels, but both fieldtypes map to
# longtext so schema sync never drops the old inline CHECK constraints.
# The checks are column-level, so DROP CONSTRAINT won't remove them;
# redefining the column via MODIFY does.
COLUMNS = (
	("Builder Page", "blocks"),
	("Builder Page", "draft_blocks"),
	("Builder Component", "block"),
	("Block Template", "block"),
)


def execute():
	if frappe.db.db_type != "mariadb":
		return
	for doctype, column in COLUMNS:
		if has_json_check(doctype, column):
			frappe.db.change_column_type(doctype, column, "longtext", nullable=True)


def has_json_check(doctype: str, column: str) -> bool:
	return bool(
		frappe.db.sql(
			"""SELECT 1 FROM information_schema.CHECK_CONSTRAINTS
			WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s""",
			(f"tab{doctype}", column),
		)
	)
