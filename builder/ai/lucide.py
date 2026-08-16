"""The Lucide icon set, server-side.

The agent emits a compact `icon: <name>` reference; the AUTHORITATIVE tree must
carry the baked SVG, because draft_blocks is what the canvas reloads and the
published page renders — an unbaked icon block is an empty square everywhere.
Bakes exactly like the frontend's lucideSVG (components/ai/lucideIcon.ts); keep
the two transforms in lockstep. The set ships as lucide_icons.json.gz, generated
from the same lucide-static package the frontend uses.
"""

import gzip
import json
import os
import re
from functools import lru_cache


@lru_cache(maxsize=1)
def icon_set() -> dict:
	path = os.path.join(os.path.dirname(__file__), "lucide_icons.json.gz")
	with gzip.open(path, "rt") as f:
		return json.load(f)


def kebab(name: str) -> str:
	name = str(name or "").strip()
	name = re.sub(r"[\s_]+", "-", name)
	return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name).lower()


def lucide_svg(name: str, stroke_width: float = 2) -> str:
	"""Inline SVG sized to FILL its wrapper block, stroke inheriting `color`.
	Returns "" for unknown names (never raises)."""
	raw = icon_set().get(kebab(name))
	if not raw:
		return ""
	svg = re.sub(r'\s*class="[^"]*"', "", raw, count=1)
	svg = re.sub(r'width="\d+"', 'width="100%"', svg, count=1)
	svg = re.sub(r'height="\d+"', 'height="100%"', svg, count=1)
	svg = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{stroke_width}"', svg, count=1)
	return svg.strip()
