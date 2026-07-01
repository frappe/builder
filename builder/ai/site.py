"""Orchestrator for AI-first multi-page site generation.

One site run has three phases, all kicked off by `run_site_job` (enqueued from the
`generate_site` endpoint):

  P0 ARCHITECT   prompt → SiteSpec (design system, nav, page manifest)
  P1 ASSETS      create theme variables, then the shared Header/Footer components
                 — SEQUENTIAL and BEFORE any page, so pages can reference them
  P2 FAN-OUT     one draft page + one enqueued sub-agent per manifest entry, in
                 parallel; each persists headlessly via page_writer

P0/P1 run on a single orchestrator worker (holding the site lock), so the ordering
invariant "shared assets exist before pages" holds with no cross-worker coordination.
P2 sub-agents each take a per-page lock and update their own batch row; one failing
never aborts the rest. Progress is durable on the Builder Site Batch doc (the review
screen reads it); realtime events are the live nudge.
"""

import json
import logging

import frappe

from builder.ai import llm, locks, page_writer
from builder.ai.prompts import Prompts
from builder.ai.site_spec import SiteSpec
from builder.utils import compact_json

logger = frappe.logger("builder.ai.site")
logger.setLevel(logging.INFO)

EVENT_PREFIX = "ai_chat"
COUNTER_FIELDS = {"completed_pages", "failed_pages"}


# --- realtime -----------------------------------------------------------


def emit_page(page_id: str, suffix: str, user: str, **payload) -> None:
	"""Emit a per-page event on the same topic the interactive editor listens to,
	so the progress view reuses attachAIChatListeners unchanged."""
	frappe.publish_realtime(f"{EVENT_PREFIX}_{suffix}_{page_id}", {"page_id": page_id, **payload}, user=user)


def emit_site(batch_id: str, **payload) -> None:
	frappe.publish_realtime(f"ai_site_{batch_id}", {"batch_id": batch_id, **payload})


# --- batch bookkeeping --------------------------------------------------


def set_batch_status(batch_id: str, status: str) -> None:
	frappe.db.set_value("Builder Site Batch", batch_id, "status", status, update_modified=False)
	frappe.db.commit()


def update_batch_page(batch_id: str, page_id: str, **fields) -> None:
	row = frappe.db.get_value("Builder Site Batch Page", {"parent": batch_id, "page": page_id}, "name")
	if row:
		frappe.db.set_value("Builder Site Batch Page", row, fields, update_modified=False)
		frappe.db.commit()


def bump_batch_counter(batch_id: str, field: str) -> None:
	"""Atomic increment so parallel sub-agents don't lose updates (a read-modify-write
	set_value would). `field` is from a fixed whitelist — never user input."""
	if field not in COUNTER_FIELDS:
		return
	frappe.db.sql(
		f"UPDATE `tabBuilder Site Batch` SET `{field}` = `{field}` + 1 WHERE name = %s",
		batch_id,
	)
	frappe.db.commit()


# --- shared design system ----------------------------------------------


def shared_design_preamble(spec: SiteSpec, header_id: str | None, footer_id: str | None) -> str:
	"""The design-system text injected into every page/component generation so the
	whole site stays consistent without cross-worker coordination."""
	lines = ["# Shared design system — use consistently across the whole site"]
	if spec.variables:
		# Push the model to reference tokens, not hardcode hex, so one edit restyles the
		# whole site. Values are shown only for reference (so it can reason about contrast).
		tokens = ", ".join(f"var(--{v.variable_name}) [{v.value}]" for v in spec.variables)
		lines.append(
			"Brand colours are THEME VARIABLES — in styles use the var(--token) form, NOT the raw "
			f"hex, so the whole site re-themes from one place. Tokens (value for reference only): {tokens}"
		)
	elif spec.palette:
		lines.append("Palette: " + ", ".join(f"{k} {v}" for k, v in spec.palette.items()))
	if spec.fonts:
		lines.append(f"Fonts — headings: {spec.fonts.get('heading', '')}, body: {spec.fonts.get('body', '')}")
	if header_id:
		lines.append(
			f"The FIRST top-level section MUST be the shared header — a block `{{el: div, component: {header_id}}}` (no other props)."
		)
	if footer_id:
		lines.append(
			f"The LAST top-level section MUST be the shared footer — a block `{{el: div, component: {footer_id}}}`."
		)
	return "\n".join(lines)


def create_theme_variables(spec: SiteSpec) -> None:
	for v in spec.variables:
		if frappe.db.exists("Builder Variable", {"variable_name": v.variable_name}):
			continue
		frappe.get_doc(
			{
				"doctype": "Builder Variable",
				"variable_name": v.variable_name,
				"type": v.type,
				"value": v.value,
				"dark_value": v.dark_value,
				"group": v.group,
			}
		).insert(ignore_permissions=True)


def build_component(kind: str, brief: str, shared_design: str, model: str, api_key: str) -> str | None:
	"""Generate one reusable component (Header/Footer) and store it as a Builder
	Component. Returns its component_id (embedded by pages via extendedFromComponent)."""
	if not brief:
		return None
	messages = [
		{"role": "system", "content": Prompts.COMPONENT_YAML},
		{"role": "user", "content": f"{shared_design}\n\n{kind} brief:\n{brief}"},
	]
	yaml_text = llm.complete(model, messages, llm.TASK_PARAMS["complex"], stream=False, api_key=api_key)
	blocks, _ = page_writer.expand_page_yaml(yaml_text, is_root=False)
	if not blocks:
		logger.warning("build_component: %s produced no blocks", kind)
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


# --- pages --------------------------------------------------------------


def create_draft_page(folder: str, page_spec) -> str:
	"""Create an empty DRAFT Builder Page under the site folder. The sub-agent fills
	its draft_blocks. Home ('/') stores route 'home'; publish maps it to the site root."""
	route = page_spec.route.strip("/") or "home"
	doc = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"page_title": page_spec.page_title,
			"route": route,
			"project_folder": folder,
			"published": 0,
			"draft_blocks": "[]",
		}
	).insert(ignore_permissions=True)
	return doc.name


# --- phase 2: per-page sub-agent (parallel) -----------------------------


def run_page_subagent(
	batch_id: str, page_id: str, brief: str, shared_design: str, model: str, api_key: str, user: str
) -> None:
	key = locks.page_key(page_id)
	if not locks.acquire(key, locks.PAGE_LOCK_TTL):
		logger.warning("run_page_subagent: page %s already locked, skipping", page_id)
		return
	try:
		update_batch_page(batch_id, page_id, status="streaming")
		emit_page(page_id, "progress", user, message="Building the page…")

		messages = [
			{"role": "system", "content": Prompts.GENERATION_YAML, "cache_control": {"type": "ephemeral"}},
			{"role": "user", "content": f"{shared_design}\n\nBuild this page now:\n{brief}"},
		]
		yaml_text = llm.complete(model, messages, llm.TASK_PARAMS["complex"], stream=False, api_key=api_key)
		if not page_writer.persist_page(page_id, yaml_text):
			raise ValueError("generation produced no blocks")

		update_batch_page(batch_id, page_id, status="done")
		bump_batch_counter(batch_id, "completed_pages")
		emit_page(page_id, "complete", user, message="Page ready")
	except Exception as e:
		logger.error("run_page_subagent failed (page=%s): %s", page_id, e, exc_info=True)
		update_batch_page(batch_id, page_id, status="failed", error=str(e)[:500])
		bump_batch_counter(batch_id, "failed_pages")
		emit_page(page_id, "error", user, message=str(e))
	finally:
		locks.release(key)
		emit_site(batch_id, phase="page", page_id=page_id)


# --- the orchestrator job (phases 0-2) ----------------------------------


def run_site_job(batch_id: str, model: str, api_key: str, user: str) -> None:
	batch = frappe.get_doc("Builder Site Batch", batch_id)
	folder = batch.project_folder
	site_lock = locks.site_key(folder)
	try:
		# P0 — architect
		emit_site(batch_id, phase="architect", status="running")
		spec = architect_site(batch.prompt, model, api_key)
		frappe.db.set_value(
			"Builder Project Folder",
			folder,
			{
				"site_spec_json": spec.to_json(),
				"nav_json": json.dumps(spec.nav, separators=(",", ":")),
				"home_page": spec.home_route,
			},
			update_modified=False,
		)
		set_batch_status(batch_id, "assets")
		emit_site(batch_id, phase="architect", status="done", pages=len(spec.pages))

		# P1 — shared assets (sequential, before any page)
		create_theme_variables(spec)
		assets_preamble = shared_design_preamble(spec, None, None)
		header_id = build_component("Header", spec.header_brief, assets_preamble, model, api_key)
		footer_id = build_component("Footer", spec.footer_brief, assets_preamble, model, api_key)
		frappe.db.set_value(
			"Builder Project Folder",
			folder,
			{"header_component": header_id or "", "footer_component": footer_id or ""},
			update_modified=False,
		)
		frappe.db.commit()
		emit_site(batch_id, phase="assets", status="done")

		# P2 — fan-out
		shared = shared_design_preamble(spec, header_id, footer_id)
		created = []
		for page_spec in spec.pages:
			page_id = create_draft_page(folder, page_spec)
			batch.append(
				"pages",
				{
					"page": page_id,
					"route": page_spec.route,
					"page_title": page_spec.page_title,
					"status": "queued",
				},
			)
			created.append((page_id, page_spec))
		batch.total_pages = len(created)
		batch.status = "generating"
		batch.save(ignore_permissions=True)
		frappe.db.commit()

		for page_id, page_spec in created:
			frappe.enqueue(
				run_page_subagent,
				queue="default",
				timeout=600,
				batch_id=batch_id,
				page_id=page_id,
				brief=page_spec.brief,
				shared_design=shared,
				model=model,
				api_key=api_key,
				user=user,
			)
		emit_site(batch_id, phase="generating", status="running", total=len(created))
	except Exception as e:
		logger.error("run_site_job failed (batch=%s): %s", batch_id, e, exc_info=True)
		set_batch_status(batch_id, "failed")
		frappe.db.set_value(
			"Builder Project Folder", folder, "generation_status", "Failed", update_modified=False
		)
		emit_site(batch_id, phase="failed", status="failed", message=str(e))
		frappe.db.commit()
	finally:
		locks.release(site_lock)


def architect_site(prompt: str, model: str, api_key: str) -> SiteSpec:
	"""P0: prompt → validated SiteSpec (heavy model, structured JSON output)."""
	messages = [
		{"role": "system", "content": Prompts.SITE_ARCHITECT_SYSTEM},
		{"role": "user", "content": prompt},
	]
	text = llm.complete(model, messages, llm.TASK_PARAMS["complex"], stream=False, api_key=api_key)
	parsed, _ = llm.loads_tolerant(text)
	if parsed is None:
		raise ValueError("architect returned unparseable JSON")
	return SiteSpec.from_llm(parsed)
