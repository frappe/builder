"""Durable turn admission and recovery; realtime is only a notification channel."""

import hashlib
import json

import frappe

ACTIVE_STATUSES = ("queued", "running")


class AIRun:
	DOCTYPE = "Builder AI Run"

	@staticmethod
	def request_name(request_id: str) -> str:
		return hashlib.sha256(f"{frappe.session.user}:{request_id}".encode()).hexdigest()[:32]

	@classmethod
	def existing(cls, request_id: str | None):
		if request_id and frappe.db.get_value(
			cls.DOCTYPE, cls.request_name(request_id), "name", for_update=True
		):
			return frappe.get_doc(cls.DOCTYPE, cls.request_name(request_id), for_update=True)

	@classmethod
	def lock_request(cls, request_id: str | None):
		"""Take admission ownership before writing any turn state.

		MariaDB snapshot isolation can reject a locking read after it waited for
		another transaction. At this boundary only validation reads have occurred.
		"""
		for attempt in range(3):
			try:
				frappe.db.get_value("User", frappe.session.user, "name", for_update=True)
				return cls.existing(request_id)
			except frappe.QueryDeadlockError:
				if attempt == 2:
					raise
				frappe.db.rollback()

	@classmethod
	def active(cls, session_id: str, for_update: bool = False):
		name = frappe.db.get_value(
			cls.DOCTYPE,
			{"session": session_id, "status": ["in", ACTIVE_STATUSES]},
			"name",
			order_by="creation desc",
			for_update=for_update,
		)
		if not name:
			return None
		doc = frappe.get_doc(cls.DOCTYPE, name, for_update=for_update)
		last_seen = doc.heartbeat_on or doc.creation
		limit = 3600 if doc.status == "queued" else 720
		if frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), last_seen) > limit:
			from builder.ai.session import AISession

			# Recheck under ownership: a queued job may have been claimed since
			# the first read, and a stale poll must not interrupt that new worker.
			doc = frappe.get_doc(cls.DOCTYPE, name, for_update=True)
			if doc.status not in ACTIVE_STATUSES:
				return None
			last_seen = doc.heartbeat_on or doc.creation
			limit = 3600 if doc.status == "queued" else 720
			if frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), last_seen) <= limit:
				return doc
			metadata = AISession.load_metadata(doc.metadata_json)
			metadata.update({"status": "error", "runId": name, "reason": "The worker stopped responding."})
			cls.finish(name, "interrupted", metadata)
			AISession.try_append_message(
				session_id,
				"assistant",
				"This run was interrupted. Review the page, then retry or continue.",
				message_type="status",
				metadata=metadata,
			)
			return None
		return doc

	@classmethod
	def admit(cls, session_id: str, page_id: str, model: str, request_id: str | None = None):
		# Serialize admission, including the queued interval before a worker claims it.
		frappe.db.get_value("Builder AI Session", session_id, "name", for_update=True)
		if frappe.db.get_value("Builder AI Session", session_id, "status") != "Active":
			raise ValueError("This chat was deleted or archived. Start a new chat to continue.")
		if existing := cls.existing(request_id):
			return existing, False
		if cls.active(session_id, for_update=True):
			return None, False
		doc = frappe.get_doc(
			{
				"doctype": cls.DOCTYPE,
				"name": cls.request_name(request_id or frappe.generate_hash(length=32)),
				"session": session_id,
				"page": page_id,
				"run_user": frappe.session.user,
				"model": model,
				"status": "queued",
				"heartbeat_on": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		return doc, True

	@classmethod
	def claim(cls, run_id: str) -> bool:
		status = frappe.db.get_value(cls.DOCTYPE, run_id, "status", for_update=True)
		if status != "queued":
			return False
		frappe.db.set_value(
			cls.DOCTYPE, run_id, {"status": "running", "heartbeat_on": frappe.utils.now_datetime()}
		)
		frappe.db.commit()  # Release admission lock before any network call.
		return True

	@classmethod
	def finish(cls, run_id: str, status: str, metadata: dict | None = None):
		current = frappe.db.get_value(cls.DOCTYPE, run_id, "status", for_update=True)
		if current not in ACTIVE_STATUSES and current != status:
			return False
		frappe.db.set_value(
			cls.DOCTYPE,
			run_id,
			{
				"status": status,
				"finished_on": frappe.utils.now_datetime(),
				"payload_json": None,
				"metadata_json": json.dumps(metadata or {}, separators=(",", ":")),
			},
		)
		return True

	@staticmethod
	def cancel_key(run_id: str) -> str:
		return f"builder_ai_cancel:{run_id}"

	@classmethod
	def cancel(cls, run_id: str):
		status = frappe.db.get_value(cls.DOCTYPE, run_id, "status", for_update=True)
		if status not in ACTIVE_STATUSES:
			return status
		frappe.db.set_value(cls.DOCTYPE, run_id, "cancel_requested", 1)
		frappe.cache.set_value(cls.cancel_key(run_id), "1", expires_in_sec=720)
		if status == "queued":
			cls.finish(run_id, "cancelled")
		return "cancelled" if status == "queued" else "cancelling"

	@staticmethod
	def public(doc) -> dict | None:
		if not doc:
			return None
		return {
			"run_id": doc.name,
			"session_id": doc.session,
			"status": doc.status,
			"model": doc.model,
			"user_message_id": doc.user_message,
		}

	@classmethod
	def enqueue(cls, run_id: str, payload: dict):
		# The row is an outbox: a failed after-commit dispatch can be retried safely.
		frappe.db.set_value(cls.DOCTYPE, run_id, "payload_json", json.dumps(payload))
		frappe.db.after_commit.add(lambda: dispatch_run(run_id))


def dispatch_run(run_id: str):
	if frappe.conf.get("builder_ai_runtime") == "async":
		return
	doc = frappe.get_doc(AIRun.DOCTYPE, run_id)
	if doc.status != "queued" or not doc.payload_json:
		return
	try:
		frappe.enqueue(
			"builder.ai.agent.loop.run_agent_job",
			queue=frappe.conf.get("builder_ai_queue") or "default",
			timeout=600,
			job_id=f"builder-ai-{run_id}",
			deduplicate=True,
			**json.loads(doc.payload_json),
		)
	except Exception:
		frappe.logger("builder.ai").exception("AI dispatch deferred; durable run %s remains queued", run_id)


def dispatch_queued_runs():
	for run_id in frappe.get_all(
		AIRun.DOCTYPE, filters={"status": "queued"}, pluck="name", limit=100, order_by="creation asc"
	):
		dispatch_run(run_id)
