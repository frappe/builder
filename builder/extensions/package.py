# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Bounded checks on a `.builderext` package before Builder writes any of it.

Builder Hub validates a package when it indexes a release, but the Hub is a code
source Builder trusts to point at a release, not one it trusts to have vetted
it. So Builder runs the same checks again here, over the exact bytes the release
`package_sha256` pins.

A package is one ZIP holding `manifest.json`, `main.js` and an optional
`icon.svg`, and nothing else. See `builder_hub.extensions.package` for the
reference these checks mirror.
"""

from __future__ import annotations

import io
import json
import posixpath
import re
import stat
import unicodedata
import xml.etree.ElementTree as ElementTree
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

import frappe
from frappe import _

from builder.extensions.constants import (
	CAPABILITIES,
	ENTRY_FILE,
	EXTENSION_NAME_PATTERN,
	MANIFEST_FILE,
	MAX_EXTRACTED_BYTES,
	MAX_ICON_BYTES,
	MAX_MANIFEST_BYTES,
	MAX_PACKAGE_FILES,
	MAX_SOURCE_BYTES,
	PACKAGE_SUFFIXES,
	PROTOCOL_VERSION,
	VERSION_PATTERN,
)

MANIFEST_REQUIRED_FIELDS = frozenset(
	{"v", "name", "label", "description", "version", "entry", "capabilities"}
)
MANIFEST_OPTIONAL_FIELDS = frozenset({"icon"})

# Every import specifier `main.js` carries, so a relative one can be refused: a
# sandboxed frame resolves it against nothing.
IMPORT_SPECIFIER = re.compile(
	r"(?:\bimport\s*(?:[^'\";]*?\sfrom\s*)?|\bexport\s+[^'\";]*?\sfrom\s*|\bimport\s*\()['\"]([^'\"]+)['\"]"
)
IMPORT_META_URL = re.compile(r"\bnew\s+URL\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*import\.meta\.url")

# A url() that is not a local fragment, or a value that opens with an external scheme.
SVG_EXTERNAL_REFERENCE = re.compile(
	r"(?:url\s*\(\s*['\"]?\s*(?!#)|^\s*(?:https?:|//|data:|javascript:))", re.I
)


@dataclass(frozen=True)
class ValidatedPackage:
	"""What a caller may write, once every check below has passed.

	`files` is keyed by the name each entry takes under the install root, ready
	for `BuilderUserExtension.write_extension_files`.
	"""

	manifest: dict
	files: dict[str, bytes]


def validate_package(package_bytes: bytes, expected_name: str, expected_version: str) -> ValidatedPackage:
	"""Every package rule, run in one place so no caller can skip one.

	Raises `frappe.ValidationError` naming the first rule the package breaks.
	"""
	with open_archive(package_bytes) as archive:
		entries = read_entries(archive)

		manifest_bytes = read_entry(archive, entries[MANIFEST_FILE], MAX_MANIFEST_BYTES)
		manifest = parse_manifest(manifest_bytes)
		assert_identity(manifest, expected_name, expected_version)
		assert_file_set(entries, manifest.get("icon"))

		files = {MANIFEST_FILE: manifest_bytes, ENTRY_FILE: read_main_js(archive, entries)}
		icon = manifest.get("icon")
		if icon:
			files[icon] = read_icon(archive, entries, icon)

	return ValidatedPackage(manifest, files)


def open_archive(package_bytes: bytes) -> zipfile.ZipFile:
	try:
		return zipfile.ZipFile(io.BytesIO(package_bytes))
	except zipfile.BadZipFile:
		frappe.throw(_("The extension package is not a valid ZIP file."))


def read_entries(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
	"""Every entry, checked and keyed by its normalized path. No two share a path."""
	infos = archive.infolist()
	if len(infos) > MAX_PACKAGE_FILES:
		frappe.throw(_("The package holds more than {0} files.").format(MAX_PACKAGE_FILES))

	extracted = 0
	entries: dict[str, zipfile.ZipInfo] = {}
	for info in infos:
		if info.is_dir():
			frappe.throw(_("The package must hold no directory: {0}.").format(info.filename))

		path = normalized_path(info.filename)
		assert_safe_entry(info, path, entries)

		extracted += info.file_size
		if extracted > MAX_EXTRACTED_BYTES:
			frappe.throw(_("The package unpacks to more than Builder allows."))
		entries[path] = info

	for required in (MANIFEST_FILE, ENTRY_FILE):
		if required not in entries:
			frappe.throw(_("The package is missing {0}.").format(required))
	return entries


def assert_safe_entry(info: zipfile.ZipInfo, path: str, seen: dict) -> None:
	if stat.S_ISLNK(info.external_attr >> 16):
		frappe.throw(_("The package holds a symbolic link: {0}.").format(info.filename))
	if info.flag_bits & 0x1:
		frappe.throw(_("The package holds an encrypted file: {0}.").format(info.filename))
	if path in seen:
		frappe.throw(_("The package names {0} twice.").format(path))
	if PurePosixPath(path).suffix not in PACKAGE_SUFFIXES:
		frappe.throw(_("The package holds an unsupported file: {0}.").format(path))


def normalized_path(name: str) -> str:
	"""One entry name as a safe relative path, or a refusal."""
	if "\x00" in name:
		frappe.throw(_("A package path holds a null byte."))

	name = unicodedata.normalize("NFC", name.replace("\\", "/"))
	if not name or PurePosixPath(name).is_absolute() or re.match(r"^[A-Za-z]:/", name):
		frappe.throw(_("Unsafe package path: {0}.").format(name))

	safe = posixpath.normpath(name)
	if safe in {".", ".."} or safe.startswith("../") or ".." in PurePosixPath(safe).parts:
		frappe.throw(_("Unsafe package path: {0}.").format(name))
	return safe


def assert_file_set(entries: dict, icon_name: str | None) -> None:
	allowed = {MANIFEST_FILE, ENTRY_FILE} | ({icon_name} if icon_name else set())
	extra = sorted(set(entries) - allowed)
	if extra:
		frappe.throw(_("The package holds an unexpected file: {0}.").format(extra[0]))


def read_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
	"""The entry's bytes, read one over the limit so an oversize one is caught."""
	with archive.open(info) as source:
		content = source.read(limit + 1)
	if len(content) > limit:
		frappe.throw(_("Package file is larger than allowed: {0}.").format(info.filename))
	return content


def parse_manifest(manifest_bytes: bytes) -> dict:
	try:
		manifest = json.loads(manifest_bytes.decode("utf-8"))
	except (UnicodeDecodeError, json.JSONDecodeError):
		frappe.throw(_("{0} must be valid UTF-8 JSON.").format(MANIFEST_FILE))
	return validate_manifest(manifest)


def validate_manifest(manifest: object) -> dict:
	"""The manifest rules, from a Hub response or a package. One owner for both."""
	if not isinstance(manifest, dict):
		frappe.throw(_("{0} must hold a JSON object.").format(MANIFEST_FILE))

	missing = MANIFEST_REQUIRED_FIELDS - manifest.keys()
	if missing:
		frappe.throw(_("{0} is missing {1}.").format(MANIFEST_FILE, sorted(missing)[0]))
	unknown = manifest.keys() - (MANIFEST_REQUIRED_FIELDS | MANIFEST_OPTIONAL_FIELDS)
	if unknown:
		frappe.throw(_("{0} has an unsupported field: {1}.").format(MANIFEST_FILE, sorted(unknown)[0]))

	if type(manifest["v"]) is not int or manifest["v"] != PROTOCOL_VERSION:
		frappe.throw(_("The manifest needs protocol {0}.").format(PROTOCOL_VERSION))
	if not EXTENSION_NAME_PATTERN.match(str(manifest["name"])):
		frappe.throw(_("The manifest name must read as publisher/name, in lowercase."))
	if not VERSION_PATTERN.match(str(manifest["version"])):
		frappe.throw(_("The manifest version holds a character it may not."))
	if manifest["entry"] != ENTRY_FILE:
		frappe.throw(_("The manifest entry must be {0}.").format(ENTRY_FILE))

	assert_plain_text(manifest["label"], "label", 80)
	assert_plain_text(manifest["description"], "description", 240)
	assert_capabilities(manifest["capabilities"])
	assert_manifest_icon(manifest.get("icon"))
	return manifest


def assert_plain_text(value: object, field: str, maximum: int) -> None:
	if not isinstance(value, str) or not 1 <= len(value) <= maximum or value.strip() != value:
		frappe.throw(_("The manifest {0} must be 1 to {1} characters.").format(field, maximum))
	if "<" in value or ">" in value or any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value):
		frappe.throw(_("The manifest {0} must be plain text.").format(field))


def assert_capabilities(capabilities: object) -> None:
	if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
		frappe.throw(_("The manifest capabilities must be a list of names."))
	if len(capabilities) != len(set(capabilities)):
		frappe.throw(_("The manifest capabilities repeat a name."))
	unknown = sorted(set(capabilities) - set(CAPABILITIES))
	if unknown:
		frappe.throw(_("The manifest asks for an unknown capability: {0}.").format(unknown[0]))


def assert_manifest_icon(icon: object) -> None:
	if icon is None:
		return
	if not isinstance(icon, str) or "/" in icon or "\\" in icon or not icon.endswith(".svg"):
		frappe.throw(_("The manifest icon must name one root SVG file."))


def assert_identity(manifest: dict, expected_name: str, expected_version: str) -> None:
	if manifest["name"] != expected_name:
		frappe.throw(_("The package is {0}, not {1}.").format(manifest["name"], expected_name))
	if manifest["version"] != expected_version:
		frappe.throw(
			_("The package is version {0}, not {1}.").format(manifest["version"], expected_version)
		)


def read_main_js(archive: zipfile.ZipFile, entries: dict) -> bytes:
	content = read_entry(archive, entries[ENTRY_FILE], MAX_SOURCE_BYTES)
	try:
		source = content.decode("utf-8")
	except UnicodeDecodeError:
		frappe.throw(_("{0} must be UTF-8.").format(ENTRY_FILE))

	specifiers = IMPORT_SPECIFIER.findall(source) + IMPORT_META_URL.findall(source)
	if any(specifier.startswith(".") for specifier in specifiers):
		frappe.throw(_("{0} must not import a relative file.").format(ENTRY_FILE))
	return content


def read_icon(archive: zipfile.ZipFile, entries: dict, icon_name: str) -> bytes:
	if icon_name not in entries:
		frappe.throw(_("The manifest names {0}, which the package does not hold.").format(icon_name))
	content = read_entry(archive, entries[icon_name], MAX_ICON_BYTES)
	assert_safe_svg(content, icon_name)
	return content


def assert_safe_svg(content: bytes, name: str) -> None:
	try:
		text = content.decode("utf-8")
	except UnicodeDecodeError:
		frappe.throw(_("{0} is not UTF-8 SVG.").format(name))

	if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
		frappe.throw(_("{0} holds a forbidden declaration.").format(name))
	if re.search(r"<\?xml-stylesheet|@import", text, re.I) or SVG_EXTERNAL_REFERENCE.search(text):
		frappe.throw(_("{0} holds an external reference.").format(name))

	try:
		root = ElementTree.fromstring(text)
	except ElementTree.ParseError:
		frappe.throw(_("{0} is not valid SVG.").format(name))

	if local_name(root.tag).lower() != "svg":
		frappe.throw(_("{0} has no <svg> root.").format(name))
	for element in root.iter():
		assert_safe_svg_element(element, name)


def assert_safe_svg_element(element: ElementTree.Element, name: str) -> None:
	if local_name(element.tag).lower() in {"script", "foreignobject"}:
		frappe.throw(_("{0} holds a forbidden element.").format(name))
	for attribute, value in element.attrib.items():
		attribute = local_name(attribute).lower()
		if attribute.startswith("on"):
			frappe.throw(_("{0} holds an event attribute.").format(name))
		if attribute in {"href", "src"} and value.strip() and not value.strip().startswith("#"):
			frappe.throw(_("{0} holds an external reference.").format(name))
		if SVG_EXTERNAL_REFERENCE.search(value):
			frappe.throw(_("{0} holds an external reference.").format(name))


def local_name(tag: str) -> str:
	"""A tag or attribute without its `{namespace}` prefix."""
	return tag.rsplit("}", 1)[-1]
