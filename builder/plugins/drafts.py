# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Plugins that Bob writes on this site.

Bob only ever writes a draft, and a draft runs only for the user who asked for it.
Everyone else keeps the shared release until that user shares the draft, so Bob
can never change the code that another user runs.

A draft is a package like any other. It is built here from Bob's module and runs
through the same `validate_package` checks as a Hub release.
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


def save_draft(slug: str, label: str, description: str, code: str, icon: str | None = None):
	"""Build, check and store a draft for the session user. Answers with the installation."""
	assert_plugin_manager()
	if not SLUG_PATTERN.fullmatch(slug or ""):
		frappe.throw(_("A plugin name holds lowercase letters, digits and hyphens."))

	plugin = f"{PUBLISHER}/{slug}"
	doc = get_or_new_installation(plugin)
	version = next_version(doc.version)
	icon_svg = lucide_icon_svg(icon)
	package = build_package(plugin, label, description, version, code, icon_svg)
	validated = validate_package(package, plugin, version)
	checksum = hashlib.sha256(package).hexdigest()[:12]

	doc.update(
		{
			"label": label,
			"description": description,
			"icon": ICON_FILE if icon_svg else None,
			"version": version,
			"draft_checksum": checksum,
			"draft_owner": frappe.session.user,
			"install_state": "Ready",
		}
	)
	doc.save()
	doc.write_plugin_files(validated.files, checksum)
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
	"""Each draft gets its own version, so the panel shows that something changed."""
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


def read_code(doc, user: str) -> str | None:
	"""The entry module of the release this user runs."""
	checksum = doc.draft_checksum if doc.draft_owner == user and doc.draft_checksum else doc.checksum
	if not checksum:
		return None
	entry = doc.install_path / checksum / ENTRY_FILE
	return entry.read_text() if entry.is_file() else None


def get_own_draft(plugin: str):
	"""Only the user who asked Bob for a draft can share it or throw it away."""
	installation = find_installation(plugin)
	doc = installation and frappe.get_doc(INSTALLATION_DOCTYPE, installation)
	if not doc or not doc.draft_checksum or doc.draft_owner != frappe.session.user:
		frappe.throw(_("You have no draft of {0}.").format(plugin), frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def share_draft(plugin: str) -> None:
	assert_plugin_manager()
	get_own_draft(plugin).share_draft()


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def discard_draft(plugin: str) -> None:
	get_own_draft(plugin).discard_draft()


@frappe.whitelist()
@has_page_read(NO_BUILDER_ACCESS)
def get_plugin_code(plugin: str) -> str | None:
	"""What the Share dialog shows. It is the code that the editor already loads for this user."""
	installation = find_installation(plugin)
	if not installation:
		return None
	return read_code(frappe.get_cached_doc(INSTALLATION_DOCTYPE, installation), frappe.session.user)


def load_report_key(user: str, token: str) -> str:
	return f"builder_plugin_load:{user}:{token}"


@frappe.whitelist(methods=["POST"])
@has_page_read(NO_BUILDER_ACCESS)
def report_load(token: str, report: dict) -> None:
	"""The editor tells Bob how its draft loaded. Keyed by user, so no one answers for another."""
	if not isinstance(report, dict) or len(json.dumps(report)) > MAX_REPORT_BYTES:
		frappe.throw(_("The load report is not valid."))
	frappe.cache.set_value(load_report_key(frappe.session.user, token), report, expires_in_sec=120)


def get_load_report(user: str, token: str) -> dict | None:
	# expires: a poll must reach redis each time, not the request-local copy of its first miss
	return frappe.cache.get_value(load_report_key(user, token), expires=True)
