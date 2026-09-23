# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.tests.extension_fixtures import (
	INSTALLATION_DOCTYPE,
	drop_installations,
	make_installation,
	make_user,
)
from builder.extensions.constants import CAPABILITIES
from builder.extensions.installations import get_user_installations
from builder.extensions.registry import (
	get_extension_source,
	install_dev_extension,
	remove_dev_extension,
)
from builder.extensions.tokens import set_extension_tokens, unset_extension_token


class TestListedInstallation(FrappeTestCase):
	"""What one row of the list carries for the editor to mount."""

	def listed(self, name):
		return next((row for row in get_user_installations() if row["name"] == name), None)

	def test_two_users_can_run_different_versions(self):
		drop_installations("acme/versioned")
		mine = make_installation("acme/versioned", version="1.0.0")
		make_installation("acme/versioned", user=make_user(), version="2.0.0")

		self.assertEqual(self.listed("acme/versioned")["installation_id"], mine.name)
		theirs = frappe.db.get_value(
			INSTALLATION_DOCTYPE, {"user": make_user(), "extension": "acme/versioned"}, "version"
		)
		self.assertEqual(theirs, "2.0.0")

	def test_carries_no_source(self):
		"""One call per extension reads that, so a list of five carries no bundles."""
		make_installation("acme/light", source="export default {};")

		self.assertNotIn("source", self.listed("acme/light"))


class TestExtensionIcon(FrappeTestCase):
	def test_refuses_a_path_that_climbs_out_of_the_install_folder(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation("acme/climber", icon="../../secrets.svg")


class TestGetExtensionSource(FrappeTestCase):
	def test_answers_with_the_entry_this_user_installed(self):
		make_installation("acme/coded", source="export const answer = 42;")

		self.assertEqual(get_extension_source("acme/coded"), "export const answer = 42;")

	def test_refuses_an_extension_this_user_has_not_installed(self):
		drop_installations("acme/absent")

		with self.assertRaises(frappe.PermissionError):
			get_extension_source("acme/absent")

	def test_refuses_another_users_copy(self):
		drop_installations("acme/private")
		make_installation("acme/private", user=make_user(), source="export const secret = 1;")

		with self.assertRaises(frappe.PermissionError):
			get_extension_source("acme/private")

	def test_refuses_an_installation_that_is_switched_off(self):
		make_installation("acme/paused", enabled=0, source="export default {};")

		with self.assertRaises(frappe.PermissionError):
			get_extension_source("acme/paused")

	def test_refuses_an_entry_larger_than_the_cap(self):
		"""The editor holds it in memory and posts it to five frames."""
		make_installation("acme/heavy", source="x" * 200)

		module = "builder.builder.doctype.builder_user_extension.builder_user_extension"
		with patch(f"{module}.MAX_SOURCE_BYTES", 100):
			with self.assertRaises(frappe.ValidationError):
				get_extension_source("acme/heavy")


class TestExtensionTokens(FrappeTestCase):
	def setUp(self):
		self.extension = "acme/material"
		make_installation(self.extension, label="Material")

		# a token insert clears a page cache, which commits, so a rollback between
		# tests does not reach these rows. Each test starts from none of its own
		for row in frappe.get_all("Builder Token", filters={"extension": ("like", "acme/%")}, pluck="name"):
			frappe.delete_doc("Builder Token", row, force=True)

	def tokens_of(self, extension=None):
		return frappe.get_all(
			"Builder Token",
			filters={"extension": extension or self.extension},
			fields=["name", "key", "token_name", "value", "dark_value", "group"],
		)

	def shade(self, key="accent-0", **over):
		return {"key": key, "token_name": "Accent 0", "type": "Color", "value": "#4285f4", **over}

	def test_creates_a_token(self):
		set_extension_tokens(self.extension, [self.shade()])

		rows = self.tokens_of()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["key"], "accent-0")
		self.assertEqual(rows[0]["value"], "#4285f4")

	def test_updates_in_place_rather_than_piling_up(self):
		set_extension_tokens(self.extension, [self.shade()])
		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		rows = self.tokens_of()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["value"], "#ea4335")

	def test_leaves_an_unmentioned_token_alone(self):
		set_extension_tokens(self.extension, [self.shade(), self.shade(key="accent-1")])
		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		self.assertEqual(len(self.tokens_of()), 2)

	def test_unset_removes_one_token(self):
		set_extension_tokens(self.extension, [self.shade(), self.shade(key="accent-1")])
		unset_extension_token(self.extension, "accent-1")

		self.assertEqual([row["key"] for row in self.tokens_of()], ["accent-0"])

	def test_keeps_one_extension_out_of_another(self):
		other = "acme/other-palette"
		make_installation(other, label="Other")
		set_extension_tokens(self.extension, [self.shade()])
		set_extension_tokens(other, [self.shade(value="#34a853")])

		self.assertEqual(len(self.tokens_of()), 1)
		self.assertEqual(self.tokens_of(other)[0]["value"], "#34a853")

	def installation_name(self):
		return frappe.db.get_value(
			INSTALLATION_DOCTYPE, {"user": frappe.session.user, "extension": self.extension}, "name"
		)

	def test_refuses_a_token_with_no_key(self):
		with self.assertRaises(frappe.ValidationError):
			set_extension_tokens(self.extension, [self.shade(key="")])

	def test_refuses_an_extension_this_user_has_not_installed(self):
		drop_installations("acme/never-installed")

		with self.assertRaises(frappe.PermissionError):
			set_extension_tokens("acme/never-installed", [self.shade()])

	def test_refuses_an_extension_without_the_capability(self):
		make_installation("acme/ungranted", capabilities=["page.read"])

		with self.assertRaises(frappe.PermissionError):
			set_extension_tokens("acme/ungranted", [self.shade()])


class TestDevExtension(FrappeTestCase):
	def setUp(self):
		self.extension = "acme/development"
		drop_installations(self.extension)
		self.previous = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		self.addCleanup(self.restore)

	def restore(self):
		frappe.conf.developer_mode = self.previous

	def installed(self):
		return frappe.db.get_value(
			INSTALLATION_DOCTYPE,
			{"user": frappe.session.user, "extension": self.extension},
			["version", "granted_capabilities"],
			as_dict=True,
		)

	def test_registers_an_installation_the_gate_accepts(self):
		install_dev_extension(self.extension, ["block.read", "ui.popover"])

		installed = self.installed()
		self.assertEqual(installed.version, "0.0.0-dev")
		self.assertEqual(frappe.parse_json(installed.granted_capabilities), ["block.read", "ui.popover"])

	def test_grants_only_what_the_manifest_asks_for(self):
		"""Both gates read this list, so a wider one would name what none allows."""
		granted = install_dev_extension(self.extension, ["block.read"])

		self.assertEqual(granted, ["block.read"])
		self.assertNotEqual(granted, list(CAPABILITIES))

	def test_refuses_a_capability_builder_does_not_have(self):
		with self.assertRaises(frappe.ValidationError):
			install_dev_extension(self.extension, ["quantum.read"])

	def test_removes_the_installation_and_the_tokens_of_the_session(self):
		install_dev_extension(self.extension, ["token.write"])
		set_extension_tokens(
			self.extension, [{"key": "a", "token_name": "A", "type": "Color", "value": "#fff"}]
		)

		remove_dev_extension(self.extension)

		self.assertIsNone(self.installed())
		self.assertFalse(frappe.db.exists("Builder Token", {"extension": self.extension}))

	def test_leaves_a_real_installation_alone(self):
		"""The name may belong to an extension the user really installed."""
		make_installation(self.extension, version="1.4.0")

		remove_dev_extension(self.extension)

		self.assertEqual(self.installed().version, "1.4.0")

	def test_refuses_to_register_outside_developer_mode(self):
		frappe.conf.developer_mode = 0

		with self.assertRaises(frappe.ValidationError):
			install_dev_extension(self.extension)
