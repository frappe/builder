"""Generic parallel sub-agent fan-out for Builder AI — event-driven, no waiting worker.

The dashboard chat agent can spawn N INDEPENDENT sub-agents that run in parallel —
one full headless `AgentRunner` each — to do work that decomposes cleanly (build the
pages of a site, generate several posts, …). This is NOT site-specific: a "build a
site" request just becomes "lay down shared theme + header/footer, then spawn one page
task per page".

Lifecycle of one `spawn_parallel_agents` call (a TERMINAL tool — it ends the turn):

  1. create a `Builder AI Batch` (+ one `Builder AI Batch Task` child per task)
  2. enqueue one `run_subagent_task` per task, persist a "building N tasks" message,
     and END the parent turn — no worker sits blocked polling for the results
  3. each settling child bumps the counters; the one that settles the batch wins the
     finalize lock, records the outcome on the conversation, and enqueues a
     CONTINUATION turn on the parent session (same pattern as the confirm-card resume)
  4. that turn reads the outcome and reports to the user / repairs failures

Progress is durable on the batch doc (the chat's task-group card polls it) and nudged
live over the parent session's realtime channel. Counters are bumped with atomic SQL
increments so parallel workers never lose an update; `reap_stale_batches` (scheduler)
finalizes a batch whose child died too hard to report back.
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
# Children run on the `long` queue — a separate worker pool from the chat turns
# (enqueued on `default`), so a burst of page builds can't starve the chat.
SUBAGENT_QUEUE = "long"
SUBAGENT_TIMEOUT = 780
# The finalize lock only picks ONE finalizer; it never blocks anyone. Generous TTL so
# a straggler child (or the reaper) can't double-resume the parent chat.
FINALIZE_LOCK_TTL = 3600


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


def finalize_key(batch_id: str) -> str:
	return f"builder_ai_batch_finalize:{batch_id}"


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
	parent_channel: str | None,
) -> None:
	"""Run ONE task as a full headless AgentRunner. Reports status to the batch + nudges
	the parent chat; the child that settles the batch finalizes it (maybe_finalize_batch).
	A failure here never aborts siblings — it's recorded and counted."""
	if is_batch_cancelled(batch_id):
		fail_task(batch_id, task_row, title, "Cancelled before start", parent_channel, user)
		maybe_finalize_batch(batch_id)
		return

	lock = locks.page_key(page_id) if page_id else locks.task_key(f"{batch_id}:{task_row}")
	with locks.guard(lock, locks.TASK_LOCK_TTL) as got:
		if not got:
			logger.warning("run_subagent_task: %s already locked, skipping", task_row)
			return  # duplicate execution — the other holder settles this task
		try:
			update_batch_task(batch_id, task_row, status="running")
			emit(
				parent_channel,
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
				parent_channel,
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
			fail_task(batch_id, task_row, title, str(e)[:500], parent_channel, user)
	frappe.db.commit()
	maybe_finalize_batch(batch_id)


def fail_task(batch_id, task_row, title, error, parent_channel, user) -> None:
	update_batch_task(batch_id, task_row, status="failed", error=error)
	bump_batch_counter(batch_id, "failed_tasks")
	emit(
		parent_channel,
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


# --- the spawn tool handler (terminal — ends the parent chat turn) -------


def spawn_parallel_agents(ctx, args: dict) -> str | None:
	"""Terminal tool: fan out INDEPENDENT tasks to parallel headless sub-agents and END
	the turn — no worker waits on them. Each task with a `page_title` gets a fresh draft
	page under a (shared) site folder; the sub-agent builds it. When the last task
	settles, the parent chat is resumed with the outcome (see maybe_finalize_batch).
	Returning a string DECLINES the spawn and the model self-corrects."""
	tasks = args.get("tasks")
	if not isinstance(tasks, list) or not tasks:
		return "DECLINED: no tasks provided. Pass a non-empty `tasks` list."
	if len(tasks) > MAX_PARALLEL_TASKS:
		return (
			f"DECLINED: too many tasks ({len(tasks)}). The max is {MAX_PARALLEL_TASKS} per call — "
			"combine related work into fewer, larger tasks."
		)
	if not frappe.has_permission("Builder Page", "create"):
		return "DECLINED: you do not have permission to create pages."

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
			# The channel the parent chat listens on — the page id for an editor
			# session, the session id for a page-less one (see AgentRunner.channel).
			parent_channel=ctx.channel,
		)
	frappe.db.commit()  # fires the after-commit enqueues

	# The turn ends here (terminal): persist the hand-off so it survives a reload —
	# the batchId rehydrates the task-group card — then emit it. The results arrive
	# in a continuation turn when the last child settles.
	message = f"Building {len(prepared)} task(s) in parallel — I'll report back here when they finish."
	metadata: dict = {"status": "complete", "batchId": batch.name}
	if ctx.activity:
		metadata["activity"] = ctx.activity  # research done before spawning survives a reload
	AISession.try_append_message(
		ctx.session_id, "assistant", message, message_type="chat", task_type="agent", metadata=metadata
	)
	frappe.db.commit()
	ctx.emit(
		"task_group",
		batch_id=batch.name,
		total=len(prepared),
		tasks=[{"row": r, "title": t, "page": p, "status": "queued"} for r, t, _, p in prepared],
	)
	ctx.emit("complete", message=message)
	return None


# --- settle: the last child finalizes and resumes the parent chat --------


def maybe_finalize_batch(batch_id: str) -> None:
	"""Called by every settling child. When the counters show the batch is fully
	settled, exactly ONE caller (Redis NX finalize lock) records the outcome and
	resumes the parent chat. Cancelled batches finalize silently — the user stopped
	the work; don't wake the agent to discuss it."""
	row = frappe.db.get_value(
		BATCH_DOCTYPE, batch_id, ["total_tasks", "completed_tasks", "failed_tasks"], as_dict=True
	)
	if not row or not row.total_tasks:
		return
	if (row.completed_tasks or 0) + (row.failed_tasks or 0) < row.total_tasks:
		return
	if not locks.acquire(finalize_key(batch_id), FINALIZE_LOCK_TTL):
		return  # another child (or the reaper) is finalizing
	cancelled = is_batch_cancelled(batch_id)
	summary = finalize_batch(batch_id, "cancelled" if cancelled else "done")
	if not cancelled:
		resume_parent_chat(batch_id, summary)


def resume_parent_chat(batch_id: str, summary: str) -> None:
	"""Durable outcome + continuation turn, mirroring the confirm-card resume
	(api.resume_agent_after_decision): the outcome message is what future context
	sees; the enqueued turn reports to the user / repairs failures without another
	prod. Skipped (message only) when the session is mid-turn — the model will see
	the outcome in its context on that turn anyway."""
	batch = frappe.db.get_value(
		BATCH_DOCTYPE, batch_id, ["session", "created_by_user", "model"], as_dict=True
	)
	if not batch or not batch.session:
		return
	AISession.try_append_message(batch.session, "assistant", summary, message_type="status")
	frappe.db.commit()
	if AISession.is_session_running(batch.session):
		return
	from builder.ai.agent.loop import run_agent_job
	from builder.ai.api import resolve_api_key
	from builder.ai.models import ModelRegistry

	try:
		api_key = resolve_api_key()
	except Exception:
		# The outcome message above is the durable record; a continuation without a
		# key (removed mid-flight) would only crash the settling child's job.
		logger.warning("resume_parent_chat: no API key — outcome recorded, continuation skipped")
		return

	prompt = (
		f"[Background update — your parallel tasks finished: {summary}] "
		"Report the outcome to the user in 1–2 sentences with clickable links to the pages. "
		"Retry or repair a failed task only when that clearly makes sense; otherwise just report."
	)
	# A page-bound parent (editor chat) listens on its page channel and expects a
	# page turn; a page-less one (session channel) expects an orchestrator turn.
	parent_page = frappe.db.get_value("Builder AI Session", batch.session, "page")
	frappe.enqueue(
		run_agent_job,
		queue="default",
		timeout=600,
		prompt=prompt,
		model=ModelRegistry.get_default(batch.model or "openrouter"),
		api_key=api_key,
		user=batch.created_by_user,
		page_id=parent_page or None,
		session_id=batch.session,
	)


def reap_stale_batches() -> None:
	"""Scheduler safety net: a hard-killed child (OOM, machine death) never bumps its
	counter, which would leave the batch 'running' forever with nobody left to finalize.
	Fail the stragglers on long-overdue batches and finalize them normally."""
	cutoff = frappe.utils.add_to_date(None, seconds=-2 * SUBAGENT_TIMEOUT)
	stale = frappe.get_all(
		BATCH_DOCTYPE, filters={"status": "running", "creation": ("<", cutoff)}, pluck="name"
	)
	for batch_id in stale:
		if not locks.acquire(finalize_key(batch_id), FINALIZE_LOCK_TTL):
			continue
		logger.warning("reap_stale_batches: finalizing overdue batch %s", batch_id)
		summary = finalize_batch(batch_id, "timeout")
		if not is_batch_cancelled(batch_id):
			resume_parent_chat(batch_id, summary)


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
