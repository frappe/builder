# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import base64
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
from builder.extensions.registry import (
	get_enabled_extensions,
	get_extension_source,
	install_dev_extension,
	remove_dev_extension,
)
from builder.extensions.tokens import set_extension_tokens, unset_extension_token


class TestGetEnabledExtensions(FrappeTestCase):
	def listed(self, name):
		return next((row for row in get_enabled_extensions() if row["name"] == name), None)

	def test_lists_an_extension_this_user_installed(self):
		make_installation("acme/enabled")

		self.assertIsNotNone(self.listed("acme/enabled"))

	def test_leaves_out_one_this_user_switched_off(self):
		make_installation("acme/off", enabled=0)

		self.assertIsNone(self.listed("acme/off"))

	def test_leaves_out_another_users_installation(self):
		"""The whole point: an extension runs for the person who installed it."""
		drop_installations("acme/theirs")
		make_installation("acme/theirs", user=make_user())

		self.assertIsNone(self.listed("acme/theirs"))

	def test_two_users_can_run_different_versions(self):
		drop_installations("acme/versioned")
		mine = make_installation("acme/versioned", version="1.0.0")
		make_installation("acme/versioned", user=make_user(), version="2.0.0")

		self.assertEqual(self.listed("acme/versioned")["installation_id"], mine.name)
		theirs = frappe.db.get_value(
			INSTALLATION_DOCTYPE, {"user": make_user(), "extension": "acme/versioned"}, "version"
		)
		self.assertEqual(theirs, "2.0.0")

	def test_leaves_out_a_development_installation(self):
		"""It has no files, and the browser adds its own entry for it."""
		make_installation("acme/dev", version="0.0.0-dev")

		self.assertIsNone(self.listed("acme/dev"))

	def test_names_the_extension(self):
		make_installation("acme/named")

		self.assertEqual(self.listed("acme/named")["name"], "acme/named")

	def test_includes_the_extensions_description(self):
		make_installation("acme/described", description="Add and manage icons.")

		self.assertEqual(self.listed("acme/described")["description"], "Add and manage icons.")

	def test_leaves_runtime_details_for_the_document_resource(self):
		make_installation("acme/granted", capabilities=["context.read", "block.read"], checksum="abc123")

		listed = self.listed("acme/granted")
		self.assertNotIn("checksum", listed)
		self.assertNotIn("capabilities", listed)

	def test_lists_an_extension_that_draws_nothing(self):
		"""Every extension needs its entry frame, whether or not it registers a surface."""
		make_installation("acme/quiet", capabilities=["page.read"])

		self.assertIsNotNone(self.listed("acme/quiet"))

	def test_carries_no_source(self):
		"""One call per extension reads that, so a list of five carries no bundles."""
		make_installation("acme/light", source="export default {};")

		self.assertNotIn("source", self.listed("acme/light"))


class TestExtensionIcon(FrappeTestCase):
	def test_arrives_as_a_data_uri(self):
		"""No route serves one user's files, so the icon travels with the list."""
		make_installation("acme/drawn", icon="icon.svg", source="export default {};")

		listed = next(row for row in get_enabled_extensions() if row["name"] == "acme/drawn")
		self.assertEqual(
			listed["icon"], f"data:image/svg+xml;base64,{base64.b64encode(b'<svg />').decode()}"
		)

	def test_is_none_when_the_package_ships_none(self):
		make_installation("acme/plainer", source="export default {};")

		listed = next(row for row in get_enabled_extensions() if row["name"] == "acme/plainer")
		self.assertIsNone(listed["icon"])

	def test_refuses_a_path_that_climbs_out_of_the_install_folder(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation("acme/climber", icon="../../secrets.svg")

	def test_refuses_a_format_the_editor_cannot_draw_at_any_size(self):
		with self.assertRaises(frappe.ValidationError):
			make_installation("acme/raster", icon="icon.png")


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

	def test_says_so_when_the_entry_is_missing(self):
		make_installation("acme/empty")

		with self.assertRaises(frappe.ValidationError):
			get_extension_source("acme/empty")

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

	def test_keeps_the_uuid_across_an_update(self):
		set_extension_tokens(self.extension, [self.shade()])
		first = self.tokens_of()[0]["name"]
		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		self.assertEqual(self.tokens_of()[0]["name"], first)

	def test_survives_a_rename_by_the_user(self):
		"""The reason `key` exists. `token_name` is editable in the UI."""
		set_extension_tokens(self.extension, [self.shade()])
		row = self.tokens_of()[0]
		frappe.db.set_value("Builder Token", row["name"], "token_name", "Brand Blue")

		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		self.assertEqual(len(self.tokens_of()), 1)

	def test_leaves_an_unmentioned_token_alone(self):
		set_extension_tokens(self.extension, [self.shade(), self.shade(key="accent-1")])
		set_extension_tokens(self.extension, [self.shade(value="#ea4335")])

		self.assertEqual(len(self.tokens_of()), 2)

	def test_unset_removes_one_token(self):
		set_extension_tokens(self.extension, [self.shade(), self.shade(key="accent-1")])
		unset_extension_token(self.extension, "accent-1")

		self.assertEqual([row["key"] for row in self.tokens_of()], ["accent-0"])

	def test_unset_is_quiet_about_a_key_that_is_gone(self):
		set_extension_tokens(self.extension, [self.shade()])
		unset_extension_token(self.extension, "never-existed")

		self.assertEqual(len(self.tokens_of()), 1)

	def test_keeps_one_extension_out_of_another(self):
		other = "acme/other-palette"
		make_installation(other, label="Other")
		set_extension_tokens(self.extension, [self.shade()])
		set_extension_tokens(other, [self.shade(value="#34a853")])

		self.assertEqual(len(self.tokens_of()), 1)
		self.assertEqual(self.tokens_of(other)[0]["value"], "#34a853")

	def test_a_token_outlives_the_user_who_installed_the_extension(self):
		"""It styles every page the site publishes, so it is not one person's."""
		set_extension_tokens(self.extension, [self.shade()])

		frappe.delete_doc(INSTALLATION_DOCTYPE, self.installation_name(), force=True)

		self.assertEqual(len(self.tokens_of()), 1)

	def installation_name(self):
		return frappe.db.get_value(
			INSTALLATION_DOCTYPE, {"user": frappe.session.user, "extension": self.extension}, "name"
		)

	def test_refuses_a_token_with_no_key(self):
		with self.assertRaises(frappe.ValidationError):
			set_extension_tokens(self.extension, [self.shade(key="")])

	def test_refuses_a_type_the_doctype_does_not_have(self):
		with self.assertRaises(frappe.ValidationError):
			set_extension_tokens(self.extension, [self.shade(type="Shadow")])

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

	def test_loading_again_follows_the_manifest(self):
		"""A developer edits the manifest, or undoes a narrowing they were testing."""
		install_dev_extension(self.extension, ["block.read"])

		granted = install_dev_extension(self.extension, ["block.read", "page.read"])

		self.assertEqual(granted, ["block.read", "page.read"])

	def test_refuses_a_capability_builder_does_not_have(self):
		with self.assertRaises(frappe.ValidationError):
			install_dev_extension(self.extension, ["quantum.read"])

	def test_keeps_an_installation_the_user_already_has(self):
		"""Building an extension you also run is the ordinary case."""
		make_installation(self.extension, version="1.4.0", capabilities=["page.read"])

		install_dev_extension(self.extension, ["block.read"])

		installed = self.installed()
		self.assertEqual(installed.version, "1.4.0")
		self.assertEqual(frappe.parse_json(installed.granted_capabilities), ["page.read"])

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
