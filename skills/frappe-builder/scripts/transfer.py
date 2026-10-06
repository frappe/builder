"""Copy a Builder page to another site together with what it needs there: components,
client scripts, tokens, uploaded fonts and /files assets."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

from tree import parse_blocks

# relative only: absolute URLs and /private/files stay as they are. A whole JSON value may
# hold spaces ("/files/My Photo.png"); inside text or CSS a URL ends at whitespace.
FILE_URL = re.compile(r"(?<=\")/files/[^\"\\?#]+(?=[\"?#])|(?<![\w/.-])/files/[^\s\"'()<>\\?#]+")
TOKEN_REF = re.compile(r"var\(--([\w-]+)\)")
COMPONENT_REF = re.compile(r'"extendedFromComponent":\s*"([^"]+)"')
FONT_REF = re.compile(r'"(?:[\w-]+:)?font-?[fF]amily":\s*"([^"]+)"')
PAGE_FIELDS = (
	*("page_title", "dynamic_route", "meta_description", "meta_image", "canonical_url", "language"),
	*("favicon", "authenticated_access", "disable_indexing", "head_html", "body_html", "page_data_script"),
)
TOKEN_FIELDS = ("token_name", "type", "value", "dark_value", "group")


class SiteCopy:
	"""Reads the page and everything it needs from the source and downloads every file
	before writing anything, so a missing file leaves the target untouched. On the target it
	creates what is missing and leaves what differs, unless replace is set: a component,
	script or token there may serve other pages."""

	def __init__(self, source, target, replace: bool = False):
		self.source, self.target, self.replace = source, target, replace
		self.downloads: dict[str, Path] = {}
		self.uploaded: dict[str, str] = {}
		self.docs: list[tuple[str, str, dict]] = []
		self.seen: set[tuple[str, str]] = set()
		self.tmp = Path(tempfile.mkdtemp(prefix="builder-copy-"))

	def page(self, name: str):
		try:
			self.copy_page(self.source.get("Builder Page", name))
		finally:
			shutil.rmtree(self.tmp, ignore_errors=True)

	def copy_page(self, doc: dict):
		current = self.target_page(doc["route"])
		tree = parse_blocks(doc.get("draft_blocks")) or parse_blocks(doc.get("blocks"))
		if doc.get("published") and tree != parse_blocks(doc.get("blocks")):
			print("copying the source's draft, which has edits it hasn't published")
		fields = {key: doc[key] for key in PAGE_FIELDS if doc.get(key) not in (None, "", 0)}
		fields["draft_blocks"] = tree
		self.collect(fields)
		scripts = [row["builder_script"] for row in doc.get("client_scripts") or []]
		for script in scripts:
			self.script(script)
		self.upload()
		for doctype, docname, doc_fields in self.docs:
			self.write(doctype, docname, self.rewrite(doc_fields))
		fields = self.rewrite(fields)
		fields["draft_blocks"] = json.dumps(fields["draft_blocks"], separators=(",", ":"))
		fields["client_scripts"] = [{"builder_script": script} for script in scripts]
		self.save_page(doc["route"], fields, current)

	def target_page(self, route: str) -> dict | None:
		"""The page at route on the target, checked before anything is written there."""
		found = self.target.names("Builder Page", f"route={route}")
		if not found:
			return None
		current = self.target.get("Builder Page", found[0]["name"])
		draft = parse_blocks(current.get("draft_blocks"))
		pending = draft and draft != parse_blocks(current.get("blocks"))
		if (
			pending
			and not self.replace
			and current["modified_by"] != self.target.run("auth", "whoami")["user"]
		):
			sys.exit(
				f"/{route} on the target has unpublished edits by {current['modified_by']}: publish or discard"
				" them there, or pass --replace (a snapshot is taken first)"
			)
		return current

	def save_page(self, route: str, fields: dict, current: dict | None):
		if current:
			name = current["name"]
			self.update_page(current, fields)
		else:
			name = self.target.run_input({"route": route, **fields}, "doc", "create", "Builder Page")["name"]
			print(f"created page {name} at /{route}")
		print(
			f"review the draft in the editor, then publish it: pull {name} and publish with -s {self.target.profile}"
		)

	def update_page(self, current: dict, fields: dict):
		# everything but the draft is live at once on an existing page
		update = {key: value for key, value in fields.items() if differs(current.get(key), value)}
		kept = [key for key in update if key != "draft_blocks"] if not self.replace else []
		update = {key: value for key, value in update.items() if key not in kept}
		if update:
			self.target.run(
				"method", "call", "create_manual_snapshot", "--doctype", "Builder Page",
				"--name", current["name"], "-F", "label=Before page copy",
			)  # fmt: skip
			self.target.run_input(update, "doc", "update", "Builder Page", current["name"])
		print(f"page {current['name']} at /{current['route']}: updated {', '.join(update) or 'nothing'}")
		if kept:
			print(f"left its live {', '.join(kept)} as they were; --replace copies the source's")

	def collect(self, value):
		"""Queues everything value refers to, dependencies first, and downloads its files."""
		text = json.dumps(value)
		for url in FILE_URL.findall(text):
			self.download(url)
		for component in sorted(set(COMPONENT_REF.findall(text))):
			self.component(component)
		for token in sorted(set(TOKEN_REF.findall(text))):
			self.token(token)
		for family in sorted(set(FONT_REF.findall(text))):
			self.font(family)

	def component(self, component_id: str):
		if self.visit("Builder Component", component_id):
			doc = self.source.get("Builder Component", component_id)
			fields = {
				"component_id": component_id,
				"component_name": doc.get("component_name") or component_id,
				"block": json.loads(doc.get("block") or "{}"),
				"component_data_script": doc.get("component_data_script") or "",
			}
			self.collect(fields)
			self.docs.append(("Builder Component", component_id, fields))

	def script(self, name: str):
		if self.visit("Builder Client Script", name):
			doc = self.source.get("Builder Client Script", name)
			fields = {"script_type": doc.get("script_type"), "script": doc.get("script") or ""}
			self.collect(fields)
			self.docs.append(("Builder Client Script", name, fields))

	def token(self, name: str):
		if not self.visit("Builder Token", name):
			return
		found = self.source.names("Builder Token", f"name={name}", fields="name," + ",".join(TOKEN_FIELDS))
		if not found:
			return  # a CSS variable from a script, not a token
		fields = {key: found[0].get(key) for key in TOKEN_FIELDS}
		self.docs.append(("Builder Token", name, fields))
		if fields["type"] == "Font":
			self.font(fields["value"])

	def font(self, family: str):
		if not self.visit("User Font", family):
			return
		if found := self.source.names("User Font", f"name={family}", fields="name,font_file"):
			self.download(found[0]["font_file"])
			self.docs.append(("User Font", family, {"font_name": family, "font_file": found[0]["font_file"]}))

	def download(self, url: str):
		if url not in self.downloads:
			# a folder per file keeps same-named files from different folders apart
			local = self.tmp / str(len(self.downloads)) / Path(unquote(url)).name
			local.parent.mkdir()
			if self.source.run("file", "download", url, "-o", str(local), check=False) is False:
				# the same path on the target may be missing or hold another file
				sys.exit(f"could not download {url} from the source; fix or remove it there, then copy again")
			self.downloads[url] = local

	def upload(self):
		for url, local in self.downloads.items():
			self.uploaded[url] = self.target.run("file", "upload", str(local))["file_url"]

	def rewrite(self, fields: dict) -> dict:
		fields = json.loads(FILE_URL.sub(lambda match: self.uploaded[match.group(0)], json.dumps(fields)))
		if isinstance(fields.get("block"), dict):
			fields["block"] = json.dumps(fields["block"], separators=(",", ":"))
		return fields

	def write(self, doctype: str, name: str, fields: dict):
		if doctype != "User Font":
			self.ensure(doctype, name, fields)
		elif not self.target.names("User Font", f"name={name}"):
			self.target.run_input(fields, "doc", "create", "User Font")
			print(f"created User Font {name}")

	def ensure(self, doctype: str, name: str, fields: dict):
		existing = self.target.names(doctype, f"name={name}", fields="name," + ",".join(fields))
		if not existing:
			self.target.run_input({"name": name, **fields}, "doc", "create", doctype)
			print(f"created {doctype} {name}")
		elif any(differs(existing[0].get(key), value) for key, value in fields.items()):
			if self.replace:
				self.target.run_input(fields, "doc", "update", doctype, name)
				print(f"replaced {doctype} {name}")
			else:
				print(f"kept {doctype} {name}: it differs on the target (--replace overwrites it)")

	def visit(self, doctype: str, name: str) -> bool:
		key = (doctype, name)
		if key in self.seen:
			return False
		self.seen.add(key)
		return True


def differs(current, wanted) -> bool:
	if isinstance(wanted, list):
		current = [{"builder_script": row.get("builder_script")} for row in current or []]
	return normal(current) != normal(wanted)


def normal(value):
	if isinstance(value, str) and value[:1] in "[{":
		try:
			return json.loads(value)
		except ValueError:
			pass
	return value or None
