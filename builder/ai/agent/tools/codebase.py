"""Source-access tools: the agent reads Builder's own code for ground truth.

Experiment: instead of encoding every Builder mechanic in the system prompt,
give the agent the same moves a coding agent has — search the repo, read the
relevant region — over Builder's own source. Both tools are read-only and
sandboxed to allowlisted roots inside the builder app.
"""

import re
from pathlib import Path
from typing import ClassVar

import frappe

from builder.ai.agent.registry import Tool


class SourceRepo:
	"""Read-only, sandboxed view of the builder app's source tree."""

	ROOTS = ("frontend/src", "builder")
	EXTENSIONS: ClassVar[set[str]] = {".ts", ".vue", ".py", ".json", ".md", ".css"}
	SKIP_DIRS: ClassVar[set[str]] = {"node_modules", "__pycache__", "dist", "public", "www"}
	MAX_MATCHES = 40
	MAX_READ_LINES = 200
	MAX_LINE_CHARS = 240

	def __init__(self):
		self.app_root = Path(frappe.get_app_path("builder")).resolve().parent

	def search(self, query: str, path_filter: str | None = None) -> str:
		pattern = compile_query(query)
		matches = []
		for path in self.files():
			rel = path.relative_to(self.app_root).as_posix()
			if path_filter and path_filter not in rel:
				continue
			matches.extend(self.search_file(path, rel, pattern))
			if len(matches) > self.MAX_MATCHES:
				break
		if not matches:
			return f"No matches for {query!r}. Try a broader pattern or drop the path filter."
		truncated = len(matches) > self.MAX_MATCHES
		lines = matches[: self.MAX_MATCHES]
		suffix = "\n… more matches truncated — narrow the query or add a path filter." if truncated else ""
		return "\n".join(lines) + suffix

	def search_file(self, path: Path, rel: str, pattern: re.Pattern) -> list[str]:
		try:
			text = path.read_text(errors="replace")
		except OSError:
			return []
		return [
			f"{rel}:{n}: {line.strip()[: self.MAX_LINE_CHARS]}"
			for n, line in enumerate(text.splitlines(), 1)
			if pattern.search(line)
		]

	def read(self, rel_path: str, start_line: int = 1) -> str:
		path = self.resolve(rel_path)
		if path is None:
			return f"Path {rel_path!r} is outside the readable source roots {self.ROOTS}."
		if path.is_dir():
			return self.list_dir(path)
		if not path.is_file():
			return f"No such file: {rel_path}. Use search_source or read a parent directory to find it."
		lines = path.read_text(errors="replace").splitlines()
		start = max(start_line, 1)
		chunk = lines[start - 1 : start - 1 + self.MAX_READ_LINES]
		body = "\n".join(f"{n}\t{line[: self.MAX_LINE_CHARS]}" for n, line in enumerate(chunk, start))
		if start - 1 + len(chunk) < len(lines):
			body += f"\n… file continues ({len(lines)} lines total) — call again with start_line={start + len(chunk)}."
		return body

	def list_dir(self, path: Path) -> str:
		entries = []
		for child in sorted(path.iterdir()):
			if child.name in self.SKIP_DIRS or child.name.startswith("."):
				continue
			if child.is_dir():
				entries.append(child.name + "/")
			elif child.suffix in self.EXTENSIONS:
				entries.append(child.name)
		rel = path.relative_to(self.app_root).as_posix()
		return f"{rel}/ contains:\n" + "\n".join(entries)

	def files(self):
		for root in self.ROOTS:
			for path in sorted((self.app_root / root).rglob("*")):
				if path.suffix in self.EXTENSIONS and path.is_file() and not self.skipped(path):
					yield path

	def skipped(self, path: Path) -> bool:
		return any(part in self.SKIP_DIRS for part in path.parts)

	def resolve(self, rel_path: str) -> Path | None:
		path = (self.app_root / rel_path.lstrip("/")).resolve()
		try:
			rel = path.relative_to(self.app_root).as_posix()
		except ValueError:
			return None
		allowed = any(rel == root or rel.startswith(root + "/") for root in self.ROOTS)
		return path if allowed and not self.skipped(path) else None


def compile_query(query: str) -> re.Pattern:
	try:
		return re.compile(query, re.IGNORECASE)
	except re.error:
		return re.compile(re.escape(query), re.IGNORECASE)


def run_search_source(ctx, args: dict) -> str:
	query = (args.get("query") or "").strip()
	if not query:
		return "Pass a non-empty query."
	return SourceRepo().search(query, args.get("path_filter"))


def run_read_source(ctx, args: dict) -> str:
	rel_path = (args.get("path") or "").strip()
	if not rel_path:
		return "Pass a path relative to the builder app root, e.g. frontend/src/block.ts."
	return SourceRepo().read(rel_path, int(args.get("start_line") or 1))


search_source = Tool(
	name="search_source",
	side="server",
	handler=run_search_source,
	description=(
		"Search Frappe Builder's own source code (regex, case-insensitive) and get back "
		"file:line matches. The source is the ground truth for how Builder actually works — "
		"use it when unsure about a mechanic: what fields a block supports, how styles/"
		"breakpoints/classes are applied, how repeat/bind, dynamic values, scripts, or "
		"components behave. Search first, then read_source the exact region. Do NOT use it "
		"for design taste or page content — only for Builder behaviour."
	),
	parameters={
		"type": "object",
		"properties": {
			"query": {
				"type": "string",
				"description": "Regex to search for (falls back to literal text if invalid).",
			},
			"path_filter": {
				"type": "string",
				"description": "Only search files whose path contains this substring, e.g. 'frontend/src' or 'block'.",
			},
		},
		"required": ["query"],
	},
)

read_source = Tool(
	name="read_source",
	side="server",
	handler=run_read_source,
	description=(
		"Read a file (or list a directory) from Frappe Builder's source, with line numbers. "
		"Key entry points: frontend/src/block.ts (the Block model — every supported field and "
		"how styles/attributes/breakpoints are interpreted), builder/ai/block_codec.py (the "
		"YAML block format), frontend/src/utils/ (editor behaviour). Returns up to 200 lines "
		"per call; pass start_line to continue."
	),
	parameters={
		"type": "object",
		"properties": {
			"path": {
				"type": "string",
				"description": "Path relative to the builder app root, e.g. 'frontend/src/block.ts'.",
			},
			"start_line": {
				"type": "integer",
				"description": "1-based line to start reading from (default 1).",
			},
		},
		"required": ["path"],
	},
)

TOOLS = [search_source, read_source]
