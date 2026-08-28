"""Migrate Builder AI Session.messages_json blobs into Builder AI Message rows.

This is a one-way migration. After it runs, the messages_json column is gone
and code reads/writes solely against the Builder AI Message doctype.
"""

import json

import frappe


def execute():
	if not frappe.db.has_column("Builder AI Session", "messages_json"):
		# Already migrated.
		return

	# Read raw column data — the field is no longer in the doctype JSON, so we
	# query DB directly. Sessions with NULL/empty blobs are skipped silently.
	rows = frappe.db.sql(
		"SELECT name, messages_json FROM `tabBuilder AI Session` "
		"WHERE messages_json IS NOT NULL AND messages_json != '' AND messages_json != '[]'",
		as_dict=True,
	)

	migrated_messages = 0
	migrated_sessions = 0
	for row in rows:
		try:
			msgs = json.loads(row.messages_json) if row.messages_json else []
		except (json.JSONDecodeError, TypeError):
			continue
		if not isinstance(msgs, list) or not msgs:
			continue

		for m in msgs:
			if not isinstance(m, dict):
				continue
			metadata = m.get("metadata") or {}
			if not isinstance(metadata, dict):
				metadata = {}

			status = (metadata.get("status") or "").strip()
			# Strip status (it lives in its own column now) and any inline
			# attached image data URL (multi-MB base64 blobs don't belong in
			# message metadata — the new schema avoids this footgun by design).
			meta_clean = {k: v for k, v in metadata.items() if k not in ("status", "attachedImageUrl")}
			role = m.get("role")
			if role not in ("user", "assistant"):
				continue

			msg = frappe.get_doc(
				{
					"doctype": "Builder AI Message",
					"session": row.name,
					"role": role,
					"content": m.get("content") or "",
					"message_type": m.get("message_type") or "chat",
					"status": status,
					"task_type": m.get("task_type") or "",
					"block_id": m.get("block_id") or "",
					"metadata_json": json.dumps(meta_clean, separators=(",", ":")) if meta_clean else "",
				}
			)
			msg.insert(ignore_permissions=True)
			# Preserve original creation timestamp so ordering survives migration.
			if created_at := m.get("created_at"):
				frappe.db.set_value(
					"Builder AI Message", msg.name, "creation", created_at, update_modified=False
				)
			migrated_messages += 1
		migrated_sessions += 1

	frappe.db.commit()

	# Drop the now-unused column. No shim — once migrated, the old blob is gone.
	try:
		frappe.db.sql_ddl("ALTER TABLE `tabBuilder AI Session` DROP COLUMN messages_json")
	except Exception as e:
		frappe.log_error(f"Failed to drop messages_json column: {e}", "AI session migration")

	print(f"Migrated {migrated_messages} AI messages across {migrated_sessions} sessions")
