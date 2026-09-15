# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import drop_installations, make_installation
from builder.extensions.constants import ENTRY_FILE
from builder.extensions.hub import Release, apply_release, run_hub_install
from builder.extensions.package import ValidatedPackage

EXTENSION = "acme/hub-install"
ASKED = ["context.read", "block.read", "block.update"]
HUB_URL = "https://hub.example.com"

RELEASE = Release(
	name=EXTENSION,
	version="1.2.0",
	protocol_version=1,
	manifest={},
	package_url="https://example.com/package.builderext",
	package_size=10,
	package_sha256="a" * 64,
	status="Published",
)
PACKAGE = ValidatedPackage(
	manifest={"label": "Hub Install", "description": "A test extension.", "capabilities": ASKED},
	files={ENTRY_FILE: b"export {}"},
)


class TestApplyRelease(FrappeTestCase):
	"""What the install job writes once the package checks pass."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.addCleanup(drop_installations, EXTENSION)
		self.installation = make_installation(
			EXTENSION, capabilities=[], install_state="Installing", enabled=0
		)

	def apply(self, capabilities: list[str]):
		apply_release(self.installation, HUB_URL, RELEASE, PACKAGE, capabilities)
		return frappe.get_doc("Builder User Extension", self.installation.name)

	def test_grants_what_the_user_allowed_at_install(self):
		installed = self.apply(["context.read", "block.update"])
		self.assertEqual(installed.requested, ASKED)
		self.assertEqual(installed.capabilities, ["context.read", "block.update"])

	def test_grants_nothing_when_the_user_allowed_nothing(self):
		self.assertEqual(self.apply([]).capabilities, [])

	def test_drops_a_capability_the_manifest_never_asked_for(self):
		self.assertEqual(self.apply(["context.read", "page.read"]).capabilities, ["context.read"])


class TestRunHubInstall(FrappeTestCase):
	"""What the install job reports when it ends.

	The job rolls back and commits, so the row it works on is committed first.
	"""

	def setUp(self):
		drop_installations(EXTENSION)
		self.installation = make_installation(
			EXTENSION, capabilities=[], install_state="Installing", enabled=0
		).name
		frappe.db.commit()
		self.addCleanup(self.drop_committed)

	def drop_committed(self):
		drop_installations(EXTENSION)
		frappe.db.commit()

	def run_job(self, get_release: Mock):
		with (
			patch("builder.extensions.hub.get_release", get_release),
			patch("builder.extensions.hub.download_package"),
			patch("builder.extensions.hub.validate_package", return_value=PACKAGE),
			patch("frappe.publish_realtime") as publish,
			patch("frappe.log_error") as log_error,
		):
			run_hub_install(self.installation, EXTENSION, "1.2.0", HUB_URL, frappe.session.user, ASKED)
		return publish, log_error

	def test_a_cancelled_install_ends_without_a_word(self):
		self.drop_committed()
		publish, log_error = self.run_job(Mock(return_value=RELEASE))
		publish.assert_not_called()
		log_error.assert_not_called()

	def test_a_failed_install_marks_the_row_and_says_so(self):
		publish, log_error = self.run_job(Mock(side_effect=Exception("The Hub is down.")))
		state = frappe.db.get_value(
			"Builder User Extension", self.installation, ["install_state", "install_error"]
		)
		self.assertEqual(state, ("Failed", "The Hub is down."))
		log_error.assert_called_once()
		publish.assert_called_once_with(
			"builder_extension_install",
			{"extension": EXTENSION, "state": "Failed"},
			user=frappe.session.user,
			after_commit=True,
		)
