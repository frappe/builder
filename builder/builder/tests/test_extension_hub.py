# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation
from builder.extensions.constants import ENTRY_FILE
from builder.extensions.hub import Release, apply_release
from builder.extensions.package import ValidatedPackage

EXTENSION = "acme/hub-install"
ASKED = ["context.read", "block.read", "block.update"]


class TestApplyRelease(FrappeTestCase):
	"""What the install job writes once the package checks pass."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(drop_installations, EXTENSION)
		self.installation = make_installation(
			EXTENSION, capabilities=[], install_state="Installing", enabled=0
		)

	def apply(self, capabilities: list[str]):
		release = Release(
			name=EXTENSION,
			version="1.2.0",
			protocol_version=1,
			manifest={},
			package_url="https://example.com/package.builderext",
			package_size=10,
			package_sha256="a" * 64,
			status="Published",
		)
		manifest = {"label": "Hub Install", "description": "A test extension.", "capabilities": ASKED}
		package = ValidatedPackage(manifest=manifest, files={ENTRY_FILE: b"export {}"})
		apply_release(self.installation, "https://hub.example.com", release, package, capabilities)
		return frappe.get_doc("Builder User Extension", self.installation.name)

	def test_grants_what_the_user_allowed_at_install(self):
		installed = self.apply(["context.read", "block.update"])
		self.assertEqual(installed.requested, ASKED)
		self.assertEqual(installed.capabilities, ["context.read", "block.update"])

	def test_grants_nothing_when_the_user_allowed_nothing(self):
		self.assertEqual(self.apply([]).capabilities, [])

	def test_drops_a_capability_the_manifest_never_asked_for(self):
		self.assertEqual(self.apply(["context.read", "page.read"]).capabilities, ["context.read"])
