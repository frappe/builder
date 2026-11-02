"""A bounded page brief survives rolling chat history and model switches."""

import json
import re

import frappe

TEXT_FIELDS = (
	"project",
	"audience",
	"goal",
	"voice",
	"visual_direction",
	"content",
	"constraints",
	"open_questions",
)
STAGES = ("discover", "directions", "build", "refine")
MAX_BRIEF_CHARS = 24000


def validate_asset_usage(assets: list[dict], content):
	encoded = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
	for asset in assets:
		if not (
			asset.get("preview_only") or asset.get("requires_acquisition") or asset.get("role") == "reference"
		):
			continue
		for field in ("url", "thumb", "preview_url"):
			if asset.get(field) and asset[field] in encoded:
				raise ValueError(
					f"Asset {asset.get('id')} is not ready for page use. Acquire the selected original "
					"or upload a licensed file; previews must not be published."
				)


class DesignBrief:
	def __init__(self, page_id: str):
		self.page_id = page_id

	def read(self) -> dict:
		raw = frappe.db.get_value("Builder Page", self.page_id, "ai_design_brief")
		try:
			data = json.loads(raw or "{}")
		except (ValueError, TypeError):
			data = {}
		return data if isinstance(data, dict) else {}

	def update(self, patch: dict, source_message: str | None = None, user_edit=False) -> dict:
		frappe.get_doc("Builder Page", self.page_id).check_permission("write")
		frappe.db.get_value("Builder Page", self.page_id, "name", for_update=True)
		brief = self.read()
		for field in TEXT_FIELDS:
			if field in patch:
				if not isinstance(patch[field], str) or len(patch[field]) > 1500:
					raise ValueError(f"{field} must be text under 1500 characters")
				brief[field] = patch[field]
		if "stage" in patch:
			if patch["stage"] not in STAGES:
				raise ValueError("Invalid design stage")
			brief["stage"] = patch["stage"]
		from builder.ai.workspace import update_decisions

		update_decisions(brief, patch, source_message, user_edit)
		brief["revision"] = int(brief.get("revision", 0)) + 1
		brief["source_message"] = source_message
		self.save(brief)
		return brief

	def save(self, brief: dict):
		encoded = json.dumps(brief, separators=(",", ":"), ensure_ascii=False)
		if len(encoded) > MAX_BRIEF_CHARS:
			raise ValueError("The design brief is full. Shorten older notes before adding more.")
		frappe.db.set_value("Builder Page", self.page_id, "ai_design_brief", encoded, update_modified=False)

	def context(self) -> str:
		brief = self.read()
		return (
			"Saved page brief (user corrections take precedence):\n" + json.dumps(brief, ensure_ascii=False)
			if brief
			else ""
		)

	def remember_assets(self, assets: list[dict]):
		frappe.get_doc("Builder Page", self.page_id).check_permission("write")
		frappe.db.get_value("Builder Page", self.page_id, "name", for_update=True)
		brief = self.read()
		by_id = {self.asset_key(a): a for a in brief.get("assets", []) if self.asset_key(a)}
		for asset in assets:
			key = self.asset_key(asset)
			if not key:
				continue
			previous = by_id.get(key, {})
			# A search response must not turn an already acquired original back into
			# a preview, or forget the user's choice.
			by_id[key] = {**asset, **previous} if previous.get("selected") else {**previous, **asset}
		chosen = [asset for asset in by_id.values() if asset.get("selected")]
		others = [asset for asset in by_id.values() if not asset.get("selected")]
		brief["assets"] = chosen + (others[-max(0, 12 - len(chosen)) :] if len(chosen) < 12 else [])
		while len(json.dumps(brief)) > MAX_BRIEF_CHARS and len(brief["assets"]) > len(chosen):
			brief["assets"].pop(len(chosen))
		self.save(brief)

	@staticmethod
	def asset_key(asset: dict) -> str | None:
		return asset.get("id") or asset.get("url")

	def select_assets(self, reply: str):
		ids = set(re.findall(r"\[asset: ([^\]\r\n]+)\]", reply))
		if not ids:
			return
		frappe.get_doc("Builder Page", self.page_id).check_permission("write")
		frappe.db.get_value("Builder Page", self.page_id, "name", for_update=True)
		brief = self.read()
		for asset in brief.get("assets", []):
			if self.asset_key(asset) in ids:
				asset["selected"] = True
		self.save(brief)
