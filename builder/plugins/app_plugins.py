# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Plugins that a Frappe app ships with its code.

An app names its plugin project folders in the `builder_plugins` hook,
relative to the app's source folder:

    builder_plugins = ["plugin"]

A project folder has the SDK's layout: the build in `dist/`, and a
`README.md` beside it. `bench build` builds it through the app's root
`package.json`. Builder
installs each one disabled when the app installs, applies a new build on each
migrate, and removes it with the app. The Hub plays no part.
"""

import hashlib
import subprocess
import sys
from functools import cached_property
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import get_sites

from builder.plugins.access import INSTALLATION_DOCTYPE, find_installation
from builder.plugins.constants import MANIFEST_FILE
from builder.plugins.installations import describe_source
from builder.plugins.package import ValidatedPackage, validate_files

# the SDK's names, so an app's project reads as any plugin project does
BUILD_FOLDER = "dist"
# in Builder Hub's order: DESCRIPTION.md is for users, README.md for developers
README_FILES = ("DESCRIPTION.md", "README.md")


class AppPlugin:
	"""One plugin project folder that an app names in its hook."""

	def __init__(self, app: str, folder: Path):
		self.app = app
		self.folder = folder
		self.build = folder / BUILD_FOLDER

	@cached_property
	def package(self) -> ValidatedPackage:
		"""The build's files, keyed by path, through the same rules as a Hub package."""
		if not (self.build / MANIFEST_FILE).is_file():
			frappe.throw(
				_("The {0} app has no built plugin at {1}. Run bench build --app {0}.").format(
					self.app, self.build
				)
			)
		files = self.build.rglob("*")
		return validate_files(
			{
				file.relative_to(self.build).as_posix(): file.read_bytes()
				for file in sorted(files)
				if file.is_file()
			}
		)

	@property
	def readme(self) -> str | None:
		files = [self.folder / name for name in README_FILES]
		return next((file.read_text() for file in files if file.is_file()), None)

	@property
	def name(self) -> str:
		return self.package.manifest["name"]

	@cached_property
	def checksum(self) -> str:
		digest = hashlib.sha256()
		for path, content in self.package.files.items():
			digest.update(path.encode() + b"\0" + content)
		return digest.hexdigest()[:12]

	@property
	def conflict(self) -> str | None:
		"""Why the site cannot take this plugin: the Hub or another app has its name.

		A dev row is a throwaway record of a dev server load, so the app takes it over.
		"""
		row = frappe.db.get_value(
			INSTALLATION_DOCTYPE,
			{"plugin": self.name},
			["source", "hub_url", "source_app"],
			as_dict=True,
		)
		if not row or row.source_app == self.app or row.source == "Development":
			return None
		return _('The {0} app cannot install "{1}". The site has it from {2}.').format(
			self.app, self.name, describe_source(row)
		)

	def assert_installable(self) -> None:
		if self.conflict:
			frappe.throw(self.conflict)

	def install(self) -> None:
		"""Insert it disabled, or apply a new build. An update keeps `enabled` as a manager left it.

		A taken over dev row starts disabled too, so a manager sees the trust dialog before it runs.
		"""
		self.assert_installable()
		installation = find_installation(self.name)
		if installation:
			doc = frappe.get_doc(INSTALLATION_DOCTYPE, installation)
		else:
			doc = frappe.new_doc(INSTALLATION_DOCTYPE).update({"plugin": self.name})
		if doc.checksum == self.checksum and doc.readme == self.readme:
			return
		if doc.source != "App":
			doc.enabled = 0
		doc.flags.ignore_permissions = True
		doc.apply_package(
			self.package, self.checksum, {"source": "App", "source_app": self.app, "readme": self.readme}
		)


def get_plugin_folders(app: str) -> list[Path]:
	return [
		Path(frappe.get_app_source_path(app), folder)
		for folder in frappe.get_hooks("builder_plugins", app_name=app)
	]


def get_app_plugins(app: str) -> list[AppPlugin]:
	return [AppPlugin(app, folder) for folder in get_plugin_folders(app)]


def check_app_plugins(app: str) -> None:
	"""Runs before Frappe writes any of the app, so a refusal leaves nothing behind."""
	for plugin in get_app_plugins(app):
		plugin.assert_installable()


def install_app_plugins(app: str) -> None:
	for plugin in get_app_plugins(app):
		plugin.install()


def sync_app_plugins() -> None:
	"""On migrate. One app's plugin that fails must not stop the migrate for every app, so it is skipped."""
	installed = frappe.get_installed_apps()
	# a build syncs every site on the bench, and one without Builder has no plugins table
	if "builder" not in installed:
		return
	for app in installed:
		for plugin in get_app_plugins(app):
			try:
				plugin.install()
			except frappe.ValidationError as error:
				print(f"Skipped a plugin of the {app} app: {error}")


def sync_built_apps(built_apps: list[str]) -> None:
	"""After `bench build`. `bench update` migrates before it builds, so without this a new build waits for the next migrate.

	A build has no site, so each site syncs in its own process. A site that cannot connect,
	such as in a Docker image build, is skipped with a warning.
	"""
	if not any(get_plugin_folders(app) for app in built_apps):
		return
	for site in get_sites():
		command = [sys.executable, "-m", "frappe.utils.bench_helper", "frappe", "--site", site, "execute"]
		result = subprocess.run(
			[*command, "builder.plugins.app_plugins.sync_app_plugins"],
			cwd=frappe.local.sites_path,
			capture_output=True,
			text=True,
		)
		if result.returncode:
			print(f"Skipped Builder plugins on {site}: {result.stderr.strip()[-300:]}")


def remove_app_plugins(app: str) -> None:
	for installation in frappe.get_all(INSTALLATION_DOCTYPE, filters={"source_app": app}, pluck="name"):
		frappe.delete_doc(INSTALLATION_DOCTYPE, installation, ignore_permissions=True)
