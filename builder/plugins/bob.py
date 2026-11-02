# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Plugins that Bob writes on this site.

A plugin Bob writes is a package like any other: built here from Bob's module, run
through the same `validate_package` checks as a Hub release, and installed for
everyone who edits the site. Only a plugin manager can have Bob write one.
"""

import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import frappe
from frappe import _

from builder.plugins.access import (
	INSTALLATION_DOCTYPE,
	assert_plugin_manager,
	find_installation,
)
from builder.plugins.constants import ENTRY_FILE, MANIFEST_FILE, PROTOCOL_VERSION
from builder.plugins.installations import NO_BUILDER_ACCESS
from builder.plugins.package import validate_package
from builder.utils import has_page_read

PUBLISHER = "bob"
SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
ICON_FILE = "icon.svg"
FIRST_VERSION = "0.1.0"
# an <img> draws the icon, where currentColor is black. A mid grey reads on both themes
ICON_COLOR = "#7c7c7c"
MAX_REPORT_BYTES = 20_000


def save_plugin(slug: str, label: str, description: str, code: str, icon: str | None = None):
	"""Build, check and install a new release. Answers with the installation."""
	assert_plugin_manager()
	if not SLUG_PATTERN.fullmatch(slug or ""):
		frappe.throw(_("A plugin name holds lowercase letters, digits and hyphens."))

	plugin = f"{PUBLISHER}/{slug}"
	doc = get_or_new_installation(plugin)
	version = next_version(doc.version)
	icon_svg = lucide_icon_svg(icon)
	package = build_package(plugin, label, description, version, code, icon_svg)
	validated = validate_package(package, plugin, version)

	doc.update(
		{
			"label": label,
			"description": description,
			"icon": ICON_FILE if icon_svg else None,
			"version": version,
			"checksum": hashlib.sha256(package).hexdigest()[:12],
			"install_state": "Ready",
		}
	)
	doc.save()
	doc.write_plugin_files(validated.files)
	return doc


def get_or_new_installation(plugin: str):
	installation = find_installation(plugin)
	if not installation:
		return frappe.new_doc(INSTALLATION_DOCTYPE).update({"plugin": plugin, "source": "Bob", "enabled": 1})
	doc = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
	if doc.source != "Bob":
		frappe.throw(_("{0} came from {1}, so Bob cannot change it.").format(plugin, doc.source))
	return doc


def next_version(version: str | None) -> str:
	"""Each release gets its own version, so the panel shows that something changed."""
	if not re.fullmatch(r"\d+\.\d+\.\d+", version or ""):
		return FIRST_VERSION
	major, minor, patch = version.split(".")
	return f"{major}.{minor}.{int(patch) + 1}"


def lucide_icon_svg(name: str | None) -> str | None:
	from builder.ai.lucide import lucide_svg

	svg = lucide_svg((name or "").removeprefix("lucide-"))
	return svg.replace("currentColor", ICON_COLOR) if svg else None


def build_package(
	plugin: str, label: str, description: str, version: str, code: str, icon_svg: str | None
) -> bytes:
	manifest = {
		"v": PROTOCOL_VERSION,
		"name": plugin,
		"label": label,
		"description": description,
		"version": version,
		"entry": ENTRY_FILE,
	}
	if icon_svg:
		manifest["icon"] = ICON_FILE

	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(MANIFEST_FILE, json.dumps(manifest))
		archive.writestr(ENTRY_FILE, code)
		if icon_svg:
			archive.writestr(ICON_FILE, icon_svg)
	return buffer.getvalue()


def syntax_error(code: str) -> str | None:
	"""Node names the line of a syntax error, and the browser does not. Skipped where no node is installed.

	`--check` only parses, so none of the code runs here.
	"""
	node = shutil.which("node")
	if not node:
		return None
	with tempfile.TemporaryDirectory() as folder:
		# resolved, because node reports the real path and macOS keeps temp files behind a symlink
		path = (Path(folder) / "main.mjs").resolve()
		path.write_text(code)
		try:
			result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=10)
		except subprocess.TimeoutExpired:
			return None
	if result.returncode == 0:
		return None
	# the source line, the caret and the message. The node frames below them name node's own code
	lines = result.stderr.replace(str(path), ENTRY_FILE).splitlines()
	return "\n".join(
		line for line in lines if not line.lstrip().startswith("at ") and not line.startswith("Node.js")
	)[:2000].strip()


def read_code(doc) -> str | None:
	"""The entry module of the installed release."""
	entry = doc.release_path and doc.release_path / ENTRY_FILE
	return entry.read_text() if entry and entry.is_file() else None


def load_report_key(user: str, token: str) -> str:
	return f"builder_plugin_load:{user}:{token}"


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def report_load(
	token: str, report: dict, candidate_id: str | None = None, page_id: str | None = None
) -> None:
	"""The editor tells Bob how the plugin loaded. Keyed by user, so no one answers for another."""
	if not isinstance(report, dict) or len(json.dumps(report)) > MAX_REPORT_BYTES:
		frappe.throw(_("The load report is not valid."))
	if candidate_id:
		from builder.ai.artifacts import Artifact

		assert_plugin_manager()
		artifact, value = Artifact.get(candidate_id, page_id, "plugin")
		if artifact.owner != frappe.session.user or value["token"] != token:
			frappe.throw(_("This test belongs to another candidate"), frappe.PermissionError)
		if artifact.status != "testing":
			return
		value["report"] = report
		passed = bool(report.get("registered")) and not any(
			report.get(key) for key in ("error", "problems", "disabled")
		)
		artifact.status = "verified" if passed else "failed"
		artifact.payload_json = json.dumps(value)
		artifact.save(ignore_permissions=True)
	frappe.cache.set_value(load_report_key(frappe.session.user, token), report, expires_in_sec=120)


def get_load_report(user: str, token: str) -> dict | None:
	# expires: a poll must reach redis each time, not the request-local copy of its first miss
	return frappe.cache.get_value(load_report_key(user, token), expires=True)


def stage_plugin(page_id: str, args: dict, run_id: str | None = None):
	"""Keep an uninstalled candidate until its exact source passes the editor checks."""
	from builder.ai.artifacts import Artifact
	from builder.ai.revisions import digest

	assert_plugin_manager()
	slug = (args.get("name") or "").strip().removeprefix(f"{PUBLISHER}/")
	if not SLUG_PATTERN.fullmatch(slug):
		raise ValueError("A plugin name holds lowercase letters, digits and hyphens")
	code = args.get("code") or ""
	if len(code) > 100_000 or (error := syntax_error(code)):
		raise ValueError(error if len(code) <= 100_000 else "Plugin source exceeds 100 KB")
	doc = get_or_new_installation(f"{PUBLISHER}/{slug}")
	version = next_version(doc.version)
	label = str(args.get("label") or slug)[:140]
	package = build_package(f"{PUBLISHER}/{slug}", label, args.get("description") or "", version, code, None)
	validate_package(package, f"{PUBLISHER}/{slug}", version)
	value = {
		"slug": slug,
		"label": label,
		"code": code,
		"description": args.get("description") or "",
		"icon": args.get("icon"),
		"version": version,
		"base_version": doc.version,
		"token": frappe.generate_hash(length=32),
	}
	return Artifact.save(
		page_id,
		"plugin",
		value,
		identity=digest({"run": run_id, "code": code, "slug": slug}),
		run=run_id,
		status="testing",
	), value


@frappe.whitelist()
def get_candidate(page_id: str, candidate_id: str):
	from builder.ai.artifacts import Artifact

	assert_plugin_manager()
	doc, value = Artifact.get(candidate_id, page_id, "plugin")
	if doc.owner != frappe.session.user:
		frappe.throw(_("This plugin candidate belongs to another user"), frappe.PermissionError)
	return {"code": value["code"], "label": value["label"]}


def activate_candidate(payload: dict) -> str:
	from builder.ai.artifacts import Artifact

	assert_plugin_manager()
	artifact, value = Artifact.get(payload["candidate_id"], payload["page_id"], "plugin")
	frappe.db.get_value("Builder AI Artifact", artifact.name, "name", for_update=True)
	artifact.reload()
	if artifact.status == "activated":
		return "This exact plugin candidate is already installed."
	if artifact.status != "verified":
		raise ValueError("The candidate has not passed the editor checks. Ask Bob to test it again.")
	current = get_or_new_installation(f"{PUBLISHER}/{value['slug']}")
	if current.version != value["base_version"]:
		raise ValueError("The installed plugin changed since this candidate was tested. Refresh it first.")
	doc = save_plugin(value["slug"], value["label"], value["description"], value["code"], value.get("icon"))
	artifact.status = "activated"
	artifact.save(ignore_permissions=True)
	return f"Installed {doc.label} {doc.version}. It loads on the next editor reload. Registry and render checks passed; custom interactions still need a user check."
