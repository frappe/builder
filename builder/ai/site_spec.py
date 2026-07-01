"""SiteSpec — the site architect's structured plan for a multi-page website.

The architect turns one prompt into a SiteSpec: the design system (theme tokens +
fonts), the nav, briefs for the shared header/footer components, and an ordered page
manifest. It is produced by an LLM, so `from_llm` is defensive: it coerces/validates
every field and never trusts the raw JSON. The orchestrator (site.py) consumes a
validated SiteSpec to drive the shared-assets phase and the per-page fan-out.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# Hard cap on pages per run — bounds fan-out cost/concurrency regardless of what the
# model proposes. The architect prompt asks for 3-7; this is the safety ceiling.
MAX_PAGES = 8

VARIABLE_TYPES = {"Color", "Dimension"}


@dataclass
class ThemeVariable:
	variable_name: str
	value: str
	type: str = "Color"
	dark_value: str = ""
	group: str = "Brand"

	@classmethod
	def from_dict(cls, raw: dict) -> ThemeVariable | None:
		name = str(raw.get("variable_name") or raw.get("name") or "").strip().lstrip("-")
		value = str(raw.get("value") or "").strip()
		if not name or not value:
			return None
		vtype = raw.get("type") if raw.get("type") in VARIABLE_TYPES else "Color"
		return cls(
			variable_name=name,
			value=value,
			type=vtype,
			dark_value=str(raw.get("dark_value") or "").strip(),
			group=str(raw.get("group") or "Brand").strip() or "Brand",
		)


@dataclass
class PageSpec:
	route: str
	page_title: str
	purpose: str = ""
	brief: str = ""

	@classmethod
	def from_dict(cls, raw: dict) -> PageSpec | None:
		route = normalize_route(raw.get("route"))
		title = str(raw.get("page_title") or raw.get("title") or "").strip()
		if not route or not title:
			return None
		return cls(
			route=route,
			page_title=title,
			purpose=str(raw.get("purpose") or "").strip(),
			brief=str(raw.get("brief") or raw.get("purpose") or "").strip(),
		)


@dataclass
class SiteSpec:
	variables: list[ThemeVariable] = field(default_factory=list)
	palette: dict = field(default_factory=dict)
	fonts: dict = field(default_factory=dict)
	nav: list[dict] = field(default_factory=list)
	header_brief: str = ""
	footer_brief: str = ""
	pages: list[PageSpec] = field(default_factory=list)

	@classmethod
	def from_llm(cls, raw) -> SiteSpec:
		"""Build (and validate) a SiteSpec from parsed LLM JSON. Raises ValueError if the
		result has no usable pages — a site with zero pages is not a site."""
		if isinstance(raw, str):
			raw = json.loads(raw)
		if not isinstance(raw, dict):
			raise ValueError("SiteSpec must be a JSON object")

		tokens = raw.get("design_tokens") or {}
		variables = [v for v in (ThemeVariable.from_dict(x) for x in _as_list(tokens.get("variables"))) if v]
		pages = [p for p in (PageSpec.from_dict(x) for x in _as_list(raw.get("pages"))) if p]
		pages = dedupe_routes(pages)[:MAX_PAGES]
		if not pages:
			raise ValueError("SiteSpec has no valid pages")

		nav = [
			{"label": str(n.get("label") or "").strip(), "route": normalize_route(n.get("route"))}
			for n in _as_list(raw.get("nav"))
			if isinstance(n, dict) and n.get("label")
		]

		return cls(
			variables=variables,
			palette=tokens.get("palette") if isinstance(tokens.get("palette"), dict) else {},
			fonts=raw.get("fonts") if isinstance(raw.get("fonts"), dict) else {},
			nav=nav,
			header_brief=str(raw.get("header_brief") or "").strip(),
			footer_brief=str(raw.get("footer_brief") or "").strip(),
			pages=pages,
		)

	def to_dict(self) -> dict:
		return {
			"design_tokens": {
				"palette": self.palette,
				"variables": [vars(v) for v in self.variables],
			},
			"fonts": self.fonts,
			"nav": self.nav,
			"header_brief": self.header_brief,
			"footer_brief": self.footer_brief,
			"pages": [vars(p) for p in self.pages],
		}

	def to_json(self) -> str:
		return json.dumps(self.to_dict(), separators=(",", ":"))

	@property
	def home_route(self) -> str:
		return self.pages[0].route if self.pages else "/"


def _as_list(value) -> list:
	return value if isinstance(value, list) else []


def normalize_route(route) -> str:
	"""A leading-slash, lowercase, space-free route. '' / None → '' (caller rejects)."""
	route = str(route or "").strip()
	if not route:
		return ""
	route = route.replace(" ", "-").lower()
	if not route.startswith("/"):
		route = "/" + route
	# collapse duplicate slashes, drop a trailing slash (except bare root)
	while "//" in route:
		route = route.replace("//", "/")
	return route.rstrip("/") or "/"


def dedupe_routes(pages: list[PageSpec]) -> list[PageSpec]:
	seen: set[str] = set()
	out: list[PageSpec] = []
	for p in pages:
		if p.route in seen:
			continue
		seen.add(p.route)
		out.append(p)
	return out
