"""Only adjacent, explicitly independent reads may overlap. Writes remain ordered."""

from dataclasses import dataclass
from types import SimpleNamespace

import frappe
from jsonschema import Draft7Validator

INDEPENDENT_READS = frozenset(
	{"get_document", "get_doctype_schema", "list_doctypes", "query_records", "get_page_scripts"}
)


@dataclass
class ReadBatch:
	operations: list
	page_id: str
	run_id: str | None


def read_prefix(operations, registry):
	batch = []
	for operation in operations[:4]:
		tool = registry.get(operation["tool_name"])
		if not tool or tool.name not in INDEPENDENT_READS or tool.effects:
			break
		batch.append(operation)
	return batch if len(batch) > 1 else []


def perform_read(batch, operation):
	from builder.ai.agent.registry import build_default_registry
	from builder.ai.runs import AIRun

	frappe.get_doc("Builder Page", batch.page_id).check_permission("read")
	if batch.run_id:
		run = frappe.get_doc(AIRun.DOCTYPE, batch.run_id)
		if run.run_user != frappe.session.user or run.cancel_requested or run.status != "running":
			raise ValueError("This run no longer owns the read")
	tool = build_default_registry().get(operation["tool_name"])
	if not tool or tool.name not in INDEPENDENT_READS or tool.effects:
		raise ValueError("Only declared independent reads can be batched")
	try:
		Draft7Validator(tool.parameters).validate(operation["args"])
		return tool.handler(SimpleNamespace(page_id=batch.page_id), operation["args"])
	except Exception as error:
		return f"FAILED: {str(error)[:1000]}"
