"""Which models each connected provider offers: found, never listed in code.

No model list ships with Builder. For each connected provider, discovery asks the
provider what this account can call right now (builder/ai/listings.py), describes
each model from models.dev (release date, family, tool calling, image input,
context window) and keeps the frontier that the policy describes. Those land as
Builder AI Model rows, so the picker and the agent read the database rather than
the network, and an unreachable catalog only means the list doesn't move.

A discovered row is Builder's to manage: it is switched on when its model reaches
the frontier and off when newer ones push it out. Switching one on or off by hand
makes it yours, and discovery leaves it alone from then on.

The policy is frontier.json, beside this file. Any of its keys can be overridden
per site with `builder_ai_frontier` in site_config.json:
- labs: whose models count, in picker order (an OpenRouter id names its lab)
- require: tool calling, input and output modalities, a minimum context window
- exclude: id globs for tiers that don't suit agentic design work
- newest_per_family: how many versions of one family to keep
- within_days_of_newest: drop what a lab's newest model has left this far behind
- per_lab: at most this many from one lab
"""

import fnmatch
import os
from collections import Counter
from datetime import date

import frappe
import requests
from frappe.utils.caching import redis_cache

from builder.ai.listings import list_models

logger = frappe.logger("builder.ai.discovery")

MODELS_DEV_URL = "https://models.dev/api.json"
DESCRIBE_TTL = 6 * 3600
FRESH_FOR = 6 * 3600  # a provider re-checks its listing this often
RETRY_AFTER = 30 * 60  # and this soon after a failed check
FETCH_TIMEOUT = 20
POLICY_FILE = os.path.join(os.path.dirname(__file__), "frontier.json")


class Discovery:
	"""Keeps one connected provider's Builder AI Model rows on its frontier."""

	def __init__(self, provider):
		from builder.ai.presets import preset_for

		self.provider = provider
		self.preset = preset_for(provider)

	@classmethod
	def connected(cls) -> list["Discovery"]:
		"""Every enabled provider of a known kind that has a credential to list with."""
		names = frappe.get_all(
			"Builder AI Provider", filters={"enabled": 1, "api_base": ["is", "not set"]}, pluck="name"
		)
		found = [cls(frappe.get_doc("Builder AI Provider", name)) for name in names]
		return [d for d in found if d.preset and d.credential()]

	@classmethod
	def refresh_in_background(cls) -> None:
		"""Queue a sync when a provider's list is stale; the picker shows what is stored meanwhile."""
		if any(not d.is_fresh() for d in cls.connected()):
			frappe.enqueue(
				sync_stale_providers,
				queue="short",
				job_id="builder_ai_discovery",
				deduplicate=True,
				enqueue_after_commit=True,
			)

	@classmethod
	def sync_all(cls, force: bool = False) -> None:
		for discovery in cls.connected():
			if force or not discovery.is_fresh():
				discovery.sync_quietly()

	def sync_quietly(self) -> None:
		try:
			self.sync()
		except Exception as e:
			logger.warning(f"model discovery failed for {self.provider.name}: {e}")
			self.remember(RETRY_AFTER)

	def sync(self, listed: dict[str, dict] | None = None) -> list[str]:
		"""Bring the rows in line with the frontier. Returns its row names, best first.

		An empty frontier leaves the rows alone: it means the catalogs disagree with
		the policy, far more likely than a provider with nothing worth offering."""
		if listed is None:
			listed = list_models(self.preset, self.credential())
		chosen = frontier(self.candidates(listed), load_policy())
		names = DiscoveredRows(self.provider).apply(chosen) if chosen else []
		self.remember(FRESH_FOR)
		return names

	def candidates(self, listed: dict[str, dict]) -> list[dict]:
		"""Listed models with a description to judge them by; the rest can't be judged and stay out."""
		described = described_models().get(self.preset["catalog"]) or {}
		today = date.today().isoformat()
		out = []
		for model_id, own in listed.items():
			known = described.get(model_id) or {}
			if not known and not own:
				continue
			entry = {**known, **own, "id": model_id, "lab": self.lab_of(model_id)}
			entry["label"] = known.get("label") or own.get("label") or model_id
			# a listed model with no date is most likely new: catalogs lag releases
			entry["released"] = entry.get("released") or today
			out.append(entry)
		return out

	def lab_of(self, model_id: str) -> str:
		return self.preset.get("lab") or model_id.split("/", 1)[0]

	def credential(self) -> str | None:
		key = self.provider.resolved_key()
		if not key and self.preset["listing"] == "openrouter":
			from builder.ai.llm import settings_api_key

			key = settings_api_key()
		return key

	def is_fresh(self) -> bool:
		return frappe.cache.get_value(self.cache_key()) is not None

	def remember(self, seconds: int) -> None:
		frappe.cache.set_value(self.cache_key(), 1, expires_in_sec=seconds)

	def cache_key(self) -> str:
		return f"builder_ai_discovery::{self.provider.name}"


class DiscoveredRows:
	"""A provider's Builder AI Model rows, as discovery writes them."""

	def __init__(self, provider):
		self.provider = provider

	def apply(self, chosen: list[dict]) -> list[str]:
		from builder.ai.models import ModelRegistry

		names = [self.upsert(rank, model) for rank, model in enumerate(chosen, start=1)]
		self.retire(set(names))
		ModelRegistry.clear_cache()
		return names

	def upsert(self, rank: int, model: dict) -> str:
		"""Add the model, or refresh a discovered row. A row someone owns is left as it is."""
		name = f"{self.provider.route_prefix}/{model['id']}"
		facts = {
			"label": model["label"],
			"max_tokens": model.get("context") or None,
			"supports_vision": int("image" in (model.get("input") or [])),
			"frontier_rank": rank,
		}
		discovered = frappe.db.get_value("Builder AI Model", name, "discovered")
		if discovered is None:
			doc = frappe.get_doc(
				{
					"doctype": "Builder AI Model",
					"provider": self.provider.name,
					"model_id": model["id"],
					"enabled": 1,
					"discovered": 1,
					**facts,
				}
			)
			doc.flags.from_discovery = True
			doc.insert(ignore_permissions=True)
		elif discovered:
			frappe.db.set_value("Builder AI Model", name, {**facts, "enabled": 1})
		return name

	def retire(self, keep: set[str]) -> None:
		rows = frappe.get_all(
			"Builder AI Model",
			filters={"provider": self.provider.name, "discovered": 1, "enabled": 1},
			pluck="name",
		)
		for name in rows:
			if name not in keep:
				frappe.db.set_value("Builder AI Model", name, "enabled", 0)


def sync_stale_providers() -> None:
	Discovery.sync_all()


def frontier(candidates: list[dict], policy: dict) -> list[dict]:
	"""The candidates worth offering, best first: labs in policy order, newest first within each."""
	labs = policy["labs"]
	fit = [c for c in candidates if c["lab"] in labs and qualifies(c, policy)]
	fit = recent(fit, policy["within_days_of_newest"])
	fit.sort(key=lambda c: (c["released"], c["id"]), reverse=True)
	fit.sort(key=lambda c: labs.index(c["lab"]))
	kept, per_family, per_lab = [], Counter(), Counter()
	for c in fit:
		family = (c["lab"], c.get("family") or c["id"])
		if per_family[family] >= policy["newest_per_family"] or per_lab[c["lab"]] >= policy["per_lab"]:
			continue
		per_family[family] += 1
		per_lab[c["lab"]] += 1
		kept.append(c)
	return kept


def qualifies(model: dict, policy: dict) -> bool:
	need = policy["require"]
	if need.get("tool_call") and not model.get("tools"):
		return False
	if any(m not in (model.get("input") or []) for m in need.get("input") or []):
		return False
	if any(m not in (need.get("output") or ["text"]) for m in model.get("output") or ["text"]):
		return False
	if (model.get("context") or 0) < need.get("min_context", 0) or model.get("deprecated"):
		return False
	model_id = model["id"].lower()
	return not any(fnmatch.fnmatch(model_id, pattern) for pattern in policy["exclude"])


def recent(candidates: list[dict], days: int) -> list[dict]:
	"""Drop what each lab's newest model has left more than `days` behind."""
	newest: dict[str, date] = {}
	for c in candidates:
		newest[c["lab"]] = max(newest.get(c["lab"], date.min), as_date(c["released"]))
	return [c for c in candidates if (newest[c["lab"]] - as_date(c["released"])).days <= days]


def load_policy() -> dict:
	return {**frappe.get_file_json(POLICY_FILE), **(frappe.conf.get("builder_ai_frontier") or {})}


@redis_cache(ttl=DESCRIBE_TTL)
def described_models() -> dict[str, dict[str, dict]]:
	"""models.dev's description of every model in the catalogs the presets name."""
	from builder.ai.presets import catalogs

	response = requests.get(MODELS_DEV_URL, timeout=FETCH_TIMEOUT)
	response.raise_for_status()
	data = response.json()
	return {
		catalog: {
			model_id: describe(model)
			for model_id, model in ((data.get(catalog) or {}).get("models") or {}).items()
		}
		for catalog in catalogs()
	}


def describe(model: dict) -> dict:
	modalities = model.get("modalities") or {}
	return {
		"label": model.get("name") or "",
		"family": model.get("family") or "",
		"released": model.get("release_date") or "",
		"tools": bool(model.get("tool_call")),
		"input": modalities.get("input") or [],
		"output": modalities.get("output") or [],
		"context": (model.get("limit") or {}).get("context") or 0,
		"deprecated": model.get("status") == "deprecated",
	}


def as_date(value: str) -> date:
	"""models.dev dates are a day or just a month; a bad one sorts as oldest."""
	parts = [*(value or "").split("-")[:3], "01", "01"]
	try:
		return date(int(parts[0]), int(parts[1]), int(parts[2][:2]))
	except (ValueError, IndexError):
		return date.min
