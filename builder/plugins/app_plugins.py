# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Plugins that come with a Frappe app's code.

An app names its plugin project folders in the `builder_plugins` hook,
relative to its module folder, the one that holds hooks.py:

    builder_plugins = ["plugin"]

A project builds into `public/builder_plugins/<folder>` of the module. So the
build goes out as the app's other assets do, and `/assets` serves it. Builder runs
no hook on install, build or migrate. When the editor lists plugins, each app
plugin's row is made to match the build on disk. The Hub plays no part.
"""

import hashlib
from contextlib import contextmanager
from functools import cached_property
from pathlib import Path

import frappe
from frappe import _

from builder.plugins.access import INSTALLATION_DOCTYPE, find_installation
from builder.plugins.constants import APP_PLUGINS_FINGERPRINT_KEY, ENTRY_FILE, MANIFEST_FILE
from builder.plugins.package import ValidatedPackage, assert_package_size, parse_manifest, validate_files

BUILDS_FOLDER = "builder_plugins"
# in Builder Hub's order: DESCRIPTION.md is for users, README.md for developers
README_FILES = ("DESCRIPTION.md", "README.md")
SYNCED_FIELDS = (
	"label",
	"description",
	"icon",
	"version",
	"checksum",
	"readme",
	"install_state",
	"install_error",
)


class AppPlugin:
	"""One plugin project folder that an app names in its hook."""

	def __init__(self, app: str, folder: str):
		self.app = app
		self.folder = folder

	@cached_property
	def project_manifest(self) -> dict:
		"""The project's own manifest, so a plugin with no build yet still has a row that says so."""
		return parse_manifest((self.project_path / MANIFEST_FILE).read_bytes())

	@cached_property
	def has_valid_manifest(self) -> bool:
		try:
			with muted_messages():
				self.project_manifest
		except (OSError, frappe.ValidationError):
			return False
		return True

	@property
	def name(self) -> str:
		return self.project_manifest["name"]

	@property
	def fingerprint(self) -> list:
		"""Changes when any build file or project file changes. Reads no file."""
		project_files = [self.project_path / name for name in (MANIFEST_FILE, *README_FILES)]
		files = [*sorted(self.build_path.rglob("*")), *project_files]
		return [(str(file), get_stat(file)) for file in files]

	@property
	def project_path(self) -> Path:
		return get_app_folder(self.app) / self.folder

	@property
	def build_path(self) -> Path:
		return get_app_folder(self.app) / "public" / BUILDS_FOLDER / self.folder

	@property
	def build_url(self) -> str:
		return f"/assets/{self.app}/{BUILDS_FOLDER}/{self.folder}"

	@property
	def readme(self) -> str | None:
		files = [self.project_path / name for name in README_FILES]
		return next((file.read_text() for file in files if file.is_file()), None)

	def get_package(self) -> ValidatedPackage:
		"""The build's files through the same rules as a Hub package."""
		if not (self.build_path / MANIFEST_FILE).is_file():
			raise frappe.ValidationError(_("Not built. Run bench build --app {0}.").format(self.app))
		files = sorted(file for file in self.build_path.rglob("*") if file.is_file())
		with muted_messages():
			assert_package_size([file.stat().st_size for file in files])
			return validate_files(
				{file.relative_to(self.build_path).as_posix(): file.read_bytes() for file in files}
			)

	@property
	def values(self) -> dict:
		"""The row's synced fields. A missing or invalid build gives a failed row."""
		try:
			package = self.get_package()
		except frappe.ValidationError as error:
			manifest = self.project_manifest
			state = {"checksum": None, "install_state": "Failed", "install_error": str(error)}
		else:
			manifest = package.manifest
			state = {"checksum": get_checksum(package), "install_state": "Ready", "install_error": None}
		return {
			"label": manifest["label"],
			"description": manifest["description"],
			"icon": manifest.get("icon"),
			"version": manifest["version"],
			"readme": self.readme,
			**state,
		}

	def can_take(self, doc) -> bool:
		"""A dev row is a throwaway record of a dev server load, so the app takes it.

		A row from the Hub or another app keeps the name, and this plugin waits.
		"""
		return doc.source == "Development" or (doc.source == "App" and doc.source_app == self.app)

	def sync(self) -> bool:
		"""Make the row match the build. True when it wrote.

		A new row, or a taken over dev row, starts disabled, so a manager sees the trust dialog
		first. An update keeps `enabled` as a manager left it.
		"""
		installation = find_installation(self.name)
		if not installation:
			doc = frappe.new_doc(INSTALLATION_DOCTYPE, plugin=self.name)
		else:
			doc = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
			if not self.can_take(doc):
				return False
		values = self.values
		if doc.source == "App" and all(doc.get(field) == values[field] for field in SYNCED_FIELDS):
			return False
		if doc.source != "App":
			doc.enabled = 0
		doc.update({**values, "source": "App", "source_app": self.app})
		doc.save(ignore_permissions=True)
		return True


@contextmanager
def muted_messages():
	"""The panel shows a plugin's error on its row, so the list request shows no message."""
	muted, frappe.flags.mute_messages = frappe.flags.mute_messages, True
	try:
		yield
	finally:
		frappe.flags.mute_messages = muted


def get_stat(file: Path) -> tuple[int, int] | None:
	try:
		stat = file.stat()
	except FileNotFoundError:
		return None
	return stat.st_mtime_ns, stat.st_size


def get_checksum(package: ValidatedPackage) -> str:
	digest = hashlib.sha256()
	for path, content in package.files.items():
		digest.update(path.encode() + b"\0" + content)
	return digest.hexdigest()[:12]


def get_app_folder(app: str) -> Path:
	return Path(frappe.get_app_path(app))


def get_plugin_folders(app: str) -> list[str]:
	return frappe.get_hooks("builder_plugins", app_name=app)


def get_app_plugins(app: str) -> list[AppPlugin]:
	"""Leaves out a plugin with a missing or invalid manifest. Its own build fails on it and says why."""
	plugins = [AppPlugin(app, folder) for folder in get_plugin_folders(app)]
	return [plugin for plugin in plugins if plugin.has_valid_manifest]


def find_app_plugin(app: str, plugin: str) -> AppPlugin | None:
	return next((found for found in get_app_plugins(app) if found.name == plugin), None)


def sync_app_plugins() -> None:
	"""Make each app plugin's row match its build, and drop the orphan rows.

	It skips all of that while no plugin file changed since the last sync. The editor's list
	is a GET, which Frappe rolls back. So a write asks Frappe to commit, and the fingerprint
	is kept only after that commit.
	"""
	plugins = [plugin for app in frappe.get_installed_apps() for plugin in get_app_plugins(app)]
	fingerprint = hashlib.sha256(repr([plugin.fingerprint for plugin in plugins]).encode()).hexdigest()
	if frappe.cache.get_value(APP_PLUGINS_FINGERPRINT_KEY) == fingerprint:
		return
	# first, so a plugin that moved to another app gets a new row
	dropped = drop_orphan_rows(plugins)
	changed = [plugin.sync() for plugin in plugins]
	keep = lambda: frappe.cache.set_value(APP_PLUGINS_FINGERPRINT_KEY, fingerprint)  # noqa: E731
	if any(changed) or dropped:
		frappe.local.flags.commit = True
		frappe.db.after_commit.add(keep)
	else:
		keep()


def drop_orphan_rows(plugins: list[AppPlugin]) -> bool:
	"""App rows whose app does not come with that plugin now. True when it dropped one."""
	current = {(plugin.app, plugin.name) for plugin in plugins}
	rows = frappe.get_all(
		INSTALLATION_DOCTYPE, filters={"source": "App"}, fields=["name", "source_app", "plugin"]
	)
	orphans = [row.name for row in rows if (row.source_app, row.plugin) not in current]
	for installation in orphans:
		frappe.delete_doc(INSTALLATION_DOCTYPE, installation, ignore_permissions=True)
	return bool(orphans)
