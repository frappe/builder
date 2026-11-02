"""Typed answers consume the exact persisted question once, under session ownership."""

import json
import re

import frappe

INPUT_KINDS = {"choices", "input", "upload", "color_input"}


def validate_value(field: dict, item: dict):
	value = item.get("value")
	if field.get("kind") == "choices":
		options = {o.get("id", f"option-{i}"): o for i, o in enumerate(field.get("options", []))}
		selected = item.get("optionIds", [])
		if not isinstance(selected, list) or not all(isinstance(key, str) for key in selected):
			raise ValueError("Invalid choice identifiers")
		if len(set(selected)) != len(selected) or any(key not in options for key in selected):
			raise ValueError("This option no longer belongs to the question")
		if not field.get("multi") and len(selected) > 1:
			raise ValueError("Choose one option for this question")
		return [options[key].get("label") or options[key].get("value") for key in selected], selected
	if field.get("kind") == "color_input":
		if not isinstance(value, dict) or len(value) > 6:
			raise ValueError("Invalid color answer")
		if any(str(key) not in {str(i) for i in range(len(field.get("colors", [])))} for key in value):
			raise ValueError("Unknown color slot")
		if any(
			not isinstance(color, str)
			or not re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", color)
			for color in value.values()
		):
			raise ValueError("Colors must be hex values")
	elif not isinstance(value, str) or len(value) > 4000:
		raise ValueError("Answers must be text under 4000 characters")
	return value, []


def validate_card_answer(session_id: str, answer: dict | None) -> dict | None:
	if answer is None:
		return None
	if not isinstance(answer, dict) or len(json.dumps(answer)) > 16000:
		raise ValueError("Invalid or oversized card answer")
	identity = answer.get("cardId")
	if not isinstance(identity, str) or not isinstance(answer.get("answers"), list):
		raise ValueError("An answer must name its question and fields")
	row = frappe.db.get_value(
		"Builder AI Message",
		{"name": identity, "session": session_id, "role": "assistant"},
		["metadata_json", "status"],
		as_dict=True,
		for_update=True,
	)
	if not row:
		raise ValueError("This question does not belong to this chat")
	if row.status != "ui":
		raise ValueError("This question has already been answered or replaced. Continue in the latest chat.")
	metadata = json.loads(row.metadata_json or "{}")
	fields = {field.get("id", f"field-{i}"): field for i, field in enumerate(metadata.get("ui", []))}
	clean, seen = [], set()
	for item in answer["answers"]:
		if not isinstance(item, dict) or not isinstance(item.get("fieldId"), str):
			raise ValueError("Invalid question identifier")
		identity = item["fieldId"]
		if identity not in fields or identity in seen or fields[identity].get("kind") not in INPUT_KINDS:
			raise ValueError("Unknown or repeated question")
		seen.add(identity)
		value, selected = validate_value(fields[identity], item)
		clean.append({"fieldId": identity, "value": value, "optionIds": selected})
	return {"cardId": answer["cardId"], "answers": clean}


def consume_questions(session_id: str, message_id: str, answer: dict | None):
	"""Free text can steer away from a card; stale tabs cannot answer it afterwards."""
	for row in frappe.get_all(
		"Builder AI Message",
		filters={"session": session_id, "status": "ui"},
		fields=["name", "metadata_json"],
	):
		metadata = json.loads(row.metadata_json or "{}")
		matched = bool(answer and answer["cardId"] == row.name)
		metadata["answered_by" if matched else "continued_by"] = message_id
		metadata["answer"] = answer if matched else None
		frappe.db.set_value(
			"Builder AI Message",
			row.name,
			{"status": "ui_answered" if matched else "ui_replaced", "metadata_json": json.dumps(metadata)},
		)
