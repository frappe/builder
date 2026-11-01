"""Keep transaction callbacks aligned with a tool's database savepoint."""

import frappe


class ToolSavepoint:
	def __init__(self, name):
		self.name = name
		self.settled = False
		self.had_realtime_log = hasattr(frappe.local, "_realtime_log")
		self.realtime_log = list(getattr(frappe.local, "_realtime_log", None) or [])
		# Frappe 15's callback manager has no public cut() API. Preserve callback
		# identity rather than counts, since a tool may explicitly commit.
		self.callbacks = {
			name: tuple(getattr(frappe.db, name)._functions)
			for name in ("before_commit", "after_commit", "before_rollback", "after_rollback")
		}
		frappe.db.savepoint(name)
		frappe.db.after_commit.add(self.mark_settled)
		frappe.db.after_rollback.add(self.mark_settled)

	def mark_settled(self):
		self.settled = True

	def rollback(self):
		if self.settled:
			return
		frappe.db.rollback(save_point=self.name)
		cleanup = []
		for name, previous in self.callbacks.items():
			manager = getattr(frappe.db, name)
			added = [callback for callback in manager._functions if callback not in previous]
			manager._functions = type(manager._functions)(
				callback for callback in manager._functions if callback in previous
			)
			if name.endswith("rollback"):
				cleanup.extend(added)
		for callback in cleanup:
			callback()
		if self.had_realtime_log:
			frappe.local._realtime_log = self.realtime_log
		elif hasattr(frappe.local, "_realtime_log"):
			del frappe.local._realtime_log
