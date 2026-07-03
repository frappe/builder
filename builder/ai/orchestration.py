"""Generic parallel sub-agent fan-out for Builder AI.

The dashboard chat agent can spawn N INDEPENDENT sub-agents that run in parallel —
one full headless `AgentRunner` each — to do work that decomposes cleanly (build the
pages of a site, generate several posts, …). This is NOT site-specific: a "build a
site" request just becomes "lay down shared theme + header/footer, then spawn one page
task per page".

Lifecycle of one `spawn_parallel_agents` call:

  1. create a `Builder AI Batch` (+ one `Builder AI Batch Task` child per task)
  2. enqueue one `run_subagent_task` per task on a SEPARATE queue from the parent
     (so the parent's blocking join never competes with its own children for workers)
  3. JOIN: the parent tool handler polls the batch counters until every task settles
     (bounded by JOIN_TIMEOUT), then returns a compact summary to the model
  4. the model reads the summary and continues (report to user / retry a failure)

Progress is durable on the batch doc (the chat's task-group card reads it) and nudged
live over the parent session's realtime channel. Counters are bumped with atomic SQL
increments so parallel workers never lose an update.
"""

import logging

import frappe

from builder.ai import llm, locks, page_writer
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.utils import compact_json

logger = frappe.logger("builder.ai.orchestration")
logger.setLevel(logging.INFO)

BATCH_DOCTYPE = "Builder AI Batch"
TASK_DOCTYPE = "Builder AI Batch Task"
COUNTER_FIELDS = {"completed_tasks", "failed_tasks"}

MAX_PARALLEL_TASKS = 8
# Children run on the `long` queue — a separate worker pool from the parent chat turn
# (enqueued on `default`), so a parent blocked on join() can't starve its own children.
SUBAGENT_QUEUE = "long"
SUBAGENT_TIMEOUT = 780
POLL_INTERVAL = 2.0
# The parent turn (headless) is enqueued with a timeout comfortably above this so the
# join always finishes (or times out cleanly) before the RQ hard-kill.
JOIN_TIMEOUT = 840


# --- realtime (parent-scoped; mirrors AgentRunner.emit) -----------------


def emit(channel: str | None, user: str, suffix: str, **payload) -> None:
	"""Emit on the parent chat's session channel so its task-group card updates live.
	Standalone (no AgentRunner) because sub-agent workers have no parent ctx."""
	if not channel:
		return
	frappe.publish_realtime(f"ai_chat_{suffix}_{channel}", {"session_id": channel, **payload}, user=user)


# --- batch bookkeeping --------------------------------------------------


def set_batch_status(batch_id: str, status: str) -> None:
	frappe.db.set_value(BATCH_DOCTYPE, batch_id, "status", status, update_modified=False)
	frappe.db.commit()


def update_batch_task(batch_id: str, task_row: str, **fields) -> None:
	frappe.db.set_value(TASK_DOCTYPE, task_row, fields, update_modified=False)
	frappe.db.commit()


def bump_batch_counter(batch_id: str, field: str) -> None:
	"""Atomic increment so parallel sub-agents don't lose updates (a read-modify-write
	set_value would). `field` is from a fixed whitelist — never user input."""
	if field not in COUNTER_FIELDS:
		return
	frappe.db.sql(
		f"UPDATE `tab{BATCH_DOCTYPE}` SET `{field}` = `{field}` + 1 WHERE name = %s",
		batch_id,
	)
	frappe.db.commit()


# --- cancellation -------------------------------------------------------


def batch_cancel_key(batch_id: str) -> str:
	return f"builder_ai_cancel_batch:{batch_id}"


def is_batch_cancelled(batch_id: str) -> bool:
	return bool(frappe.cache.get_value(batch_cancel_key(batch_id), use_local_cache=False))


def cancel_batch(batch_id: str) -> None:
	"""Propagate a parent cancel to children: set the batch flag (stops queued-but-unstarted
	tasks at entry) and each running sub-agent's own session cancel key (its stream loop
	honors it within ~0.25s, so no more LLM spend)."""
	frappe.cache.set_value(batch_cancel_key(batch_id), "1", expires_in_sec=SUBAGENT_TIMEOUT)
	sessions = frappe.get_all(TASK_DOCTYPE, filters={"parent": batch_id}, pluck="subagent_session")
	for session in sessions:
		if session:
			frappe.cache.set_value(f"builder_ai_cancel:{session}", "1", expires_in_sec=SUBAGENT_TIMEOUT)


# --- shared assets (folder, pages, components) --------------------------


def get_or_create_site_folder(folder_name: str | None, prompt: str) -> str:
	"""Locate or create the Builder Project Folder that holds a generated site. Marks it
	as an AI site so the dashboard renders it as one."""
	if folder_name and frappe.db.exists("Builder Project Folder", folder_name):
		frappe.db.set_value(
			"Builder Project Folder",
			folder_name,
			{"is_ai_site": 1, "site_brief": prompt},
			update_modified=False,
		)
		return folder_name
	base = (folder_name or " ".join(prompt.split()[:4]) or "AI Site").strip()[:60]
	name = base
	if frappe.db.exists("Builder Project Folder", name):
		name = f"{base} {frappe.generate_hash(length=4)}"
	doc = frappe.get_doc(
		{"doctype": "Builder Project Folder", "folder_name": name, "is_ai_site": 1, "site_brief": prompt}
	).insert(ignore_permissions=True)
	return doc.name


def create_draft_page(folder: str | None, page_title: str, route: str | None = None) -> str:
	"""Create an empty DRAFT Builder Page (the sub-agent fills its draft_blocks). Home
	('/') stores route 'home'; publish maps it to the site root."""
	r = (route or page_title).strip().strip("/").lower().replace(" ", "-") or "home"
	doc = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": page_title,
			"route": r,
			"project_folder": folder or "",
			"published": 0,
			"draft_blocks": "[]",
		}
	).insert(ignore_permissions=True)
	return doc.name


def create_component_asset(kind: str, brief: str, model: str, api_key: str) -> str | None:
	"""Generate one reusable component (e.g. a shared Header/Footer) and store it as a
	Builder Component. Returns its component_id (pages embed it via extendedFromComponent)."""
	if not brief:
		return None
	messages = [
		{"role": "system", "content": Prompts.COMPONENT_YAML},
		{"role": "user", "content": f"{kind} brief:\n{brief}"},
	]
	yaml_text = llm.complete(model, messages, llm.TASK_PARAMS["complex"], stream=False, api_key=api_key)
	blocks, _ = page_writer.expand_page_yaml(yaml_text, is_root=False)
	if not blocks:
		logger.warning("create_component_asset: %s produced no blocks", kind)
		return None
	component_id = frappe.generate_hash(length=12)
	frappe.get_doc(
		{
			"doctype": "Builder Component",
			"component_name": kind,
			"component_id": component_id,
			"block": compact_json(blocks[0]),
		}
	).insert(ignore_permissions=True)
	return component_id


# --- one sub-agent (runs in its own worker) -----------------------------


def run_subagent_task(
	batch_id: str,
	task_row: str,
	title: str,
	instructions: str,
	page_id: str | None,
	model: str,
	api_key: str,
	user: str,
	parent_session: str | None,
) -> None:
	"""Run ONE task as a full headless AgentRunner. Reports status to the batch + nudges
	the parent chat. A failure here never aborts siblings — it's recorded and counted."""
	if is_batch_cancelled(batch_id):
		fail_task(batch_id, task_row, title, "Cancelled before start", parent_session, user)
		return

	lock = locks.page_key(page_id) if page_id else locks.task_key(f"{batch_id}:{task_row}")
	with locks.guard(lock, locks.TASK_LOCK_TTL) as got:
		if not got:
			logger.warning("run_subagent_task: %s already locked, skipping", task_row)
			return
		try:
			update_batch_task(batch_id, task_row, status="running")
			emit(
				parent_session,
				user,
				"progress",
				message=f"Building: {title}",
				batch_id=batch_id,
				task=task_row,
				task_status="running",
			)

			session = AISession.create_subagent_session(user=user, model=model)
			update_batch_task(batch_id, task_row, subagent_session=session.name)

			from builder.ai.agent.loop import AgentRunner
			from builder.ai.agent.registry import build_subagent_registry

			AgentRunner(
				instructions,
				model,
				api_key,
				user=user,
				page_id=page_id,
				session_id=session.name,
				registry=build_subagent_registry(),
				# The default AGENT_SYSTEM is written for the live editor canvas; a
				# fan-out child is a headless page builder with no user to ask.
				system_prompt=Prompts.SUBAGENT_SYSTEM,
				headless=True,
			).run()

			# AgentRunner.run() swallows its own errors (emits, doesn't raise), so verify
			# the goal was actually met: a page task must have produced blocks.
			if page_id and not page_has_blocks(page_id):
				raise ValueError("sub-agent produced no page content")

			update_batch_task(batch_id, task_row, status="done")
			bump_batch_counter(batch_id, "completed_tasks")
			emit(
				parent_session,
				user,
				"progress",
				message=f"Done: {title}",
				batch_id=batch_id,
				task=task_row,
				task_status="done",
				page=page_id,
			)
		except Exception as e:
			logger.error("run_subagent_task failed (task=%s): %s", task_row, e, exc_info=True)
			fail_task(batch_id, task_row, title, str(e)[:500], parent_session, user)
	frappe.db.commit()


def fail_task(batch_id, task_row, title, error, parent_session, user) -> None:
	update_batch_task(batch_id, task_row, status="failed", error=error)
	bump_batch_counter(batch_id, "failed_tasks")
	emit(
		parent_session,
		user,
		"progress",
		message=f"Failed: {title}",
		batch_id=batch_id,
		task=task_row,
		task_status="failed",
	)


def page_has_blocks(page_id: str) -> bool:
	blocks = frappe.db.get_value("Builder Page", page_id, "draft_blocks")
	return bool(blocks) and blocks.strip() not in ("", "[]", "null")


# --- the spawn tool handler (runs in the parent chat turn) --------------


def spawn_parallel_agents(ctx, args: dict) -> str:
	"""Server tool: fan out INDEPENDENT tasks to parallel headless sub-agents, wait for
	them, and return a compact summary. Each task with a `page_title` gets a fresh draft
	page under a (shared) site folder; the sub-agent builds it."""
	tasks = args.get("tasks")
	if not isinstance(tasks, list) or not tasks:
		return "No tasks provided. Pass a non-empty `tasks` list."
	if len(tasks) > MAX_PARALLEL_TASKS:
		return (
			f"Too many tasks ({len(tasks)}). The max is {MAX_PARALLEL_TASKS} per call — "
			"combine related work into fewer, larger tasks."
		)
	if not frappe.has_permission("Builder Page", "create"):
		return "You do not have permission to create pages."

	shared = (args.get("shared_context") or "").strip()
	builds_pages = any(t.get("page_title") for t in tasks)
	folder = get_or_create_site_folder(args.get("site_name"), shared or "AI Site") if builds_pages else None

	batch = frappe.get_doc(
		{
			"doctype": BATCH_DOCTYPE,
			"batch_id": frappe.generate_hash(length=12),
			"session": ctx.session_id,
			"project_folder": folder or "",
			"model": ctx.model,
			"status": "running",
			"created_by_user": ctx.user,
		}
	)
	prepared: list[tuple] = []
	for t in tasks:
		title = (t.get("title") or t.get("page_title") or "Task").strip()
		instructions = (t.get("instructions") or "").strip()
		page_id = create_draft_page(folder, t["page_title"], t.get("route")) if t.get("page_title") else None
		row = batch.append(
			"tasks", {"title": title, "instructions": instructions, "page": page_id or "", "status": "queued"}
		)
		full = f"{shared}\n\n{instructions}" if shared else instructions
		prepared.append((row.name, title, full, page_id))
	batch.total_tasks = len(prepared)
	batch.insert(ignore_permissions=True)

	for row_name, title, full_instructions, page_id in prepared:
		frappe.enqueue(
			run_subagent_task,
			queue=SUBAGENT_QUEUE,
			timeout=SUBAGENT_TIMEOUT,
			enqueue_after_commit=True,
			batch_id=batch.name,
			task_row=row_name,
			title=title,
			instructions=full_instructions,
			page_id=page_id,
			model=ctx.model,
			api_key=ctx.api_key,
			user=ctx.user,
			parent_session=ctx.session_id,
		)
	frappe.db.commit()  # fires the after-commit enqueues

	ctx.emit(
		"task_group",
		batch_id=batch.name,
		total=len(prepared),
		tasks=[{"row": r, "title": t, "page": p, "status": "queued"} for r, t, _, p in prepared],
	)
	return join_batch(ctx, batch.name)


def join_batch(ctx, batch_id: str) -> str:
	"""Block until every task settles (or JOIN_TIMEOUT). Commit each poll iteration so a
	long-lived parent worker sees other workers' committed counter bumps (MySQL
	REPEATABLE READ would otherwise pin a stale snapshot for the whole transaction)."""
	import time

	deadline = time.monotonic() + JOIN_TIMEOUT
	while True:
		frappe.db.commit()  # end the txn → next read sees children's committed progress
		row = frappe.db.get_value(
			BATCH_DOCTYPE,
			batch_id,
			["total_tasks", "completed_tasks", "failed_tasks"],
			as_dict=True,
		)
		total = (row.total_tasks or 0) if row else 0
		settled = (row.completed_tasks or 0) + (row.failed_tasks or 0) if row else 0
		if total and settled >= total:
			return finalize_batch(batch_id, "done")
		if ctx.is_cancelled():
			cancel_batch(batch_id)
			return finalize_batch(batch_id, "cancelled")
		if time.monotonic() >= deadline:
			return finalize_batch(batch_id, "timeout")
		ctx.interruptible_sleep(POLL_INTERVAL)


def finalize_batch(batch_id: str, outcome: str) -> str:
	"""Mark unfinished tasks, set batch status, and return a compact summary for the model."""
	batch = frappe.get_doc(BATCH_DOCTYPE, batch_id)
	if outcome in ("cancelled", "timeout"):
		for t in batch.tasks:
			if t.status in ("queued", "running"):
				t.db_set("status", "failed", update_modified=False)
				t.db_set("error", outcome, update_modified=False)
		batch.reload()
	done = [t for t in batch.tasks if t.status == "done"]
	failed = [t for t in batch.tasks if t.status == "failed"]
	status = (
		"cancelled"
		if outcome == "cancelled"
		else ("done" if done and not failed else "failed" if not done else "done")
	)
	set_batch_status(batch_id, status)

	parts = [f"Spawned {len(batch.tasks)} task(s)."]
	if done:
		parts.append(f"Completed {len(done)}: {', '.join(t.title for t in done)}.")
	if failed:
		parts.append(
			"Failed "
			+ str(len(failed))
			+ ": "
			+ "; ".join(f"{t.title} ({t.error or 'unknown'})" for t in failed)
			+ "."
		)
	if batch.project_folder:
		parts.append(f"Pages are drafts under folder '{batch.project_folder}'.")
	return " ".join(parts)
