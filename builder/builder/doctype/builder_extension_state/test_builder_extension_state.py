# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_extension_state.builder_extension_state import (
	TABLE,
	UNIQUE_INDEX,
	on_doctype_update,
)
from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_user,
)
from builder.extensions.state import STATE_DOCTYPE, get_state, read_patch, set_state, unset_state

EXTENSION = "acme/remembers"


class TestExtensionState(FrappeTestCase):
	"""One user's drawer for one extension.

	It lived in `localStorage`, which is per browser, so two people sharing a
	machine shared every extension's state.
	"""

	def setUp(self):
		drop_installations(EXTENSION)
		self.installation = make_installation(EXTENSION)

	def rows(self):
		return frappe.get_all(
			STATE_DOCTYPE, filters={"installation": self.installation.name}, pluck="state_key"
		)

	def test_answers_with_nothing_before_anything_is_stored(self):
		self.assertEqual(get_state(EXTENSION), {})

	def test_stores_and_reads_a_value_back(self):
		set_state(EXTENSION, {"theme": "dark"})

		self.assertEqual(get_state(EXTENSION), {"theme": "dark"})

	def test_merges_and_never_removes_what_a_call_leaves_unmentioned(self):
		set_state(EXTENSION, {"theme": "dark"})
		set_state(EXTENSION, {"page": 2})

		self.assertEqual(get_state(EXTENSION), {"theme": "dark", "page": 2})

	def test_one_row_per_key_so_two_frames_never_race(self):
		set_state(EXTENSION, {"theme": "dark", "page": 2})

		self.assertEqual(sorted(self.rows()), ["page", "theme"])

	def test_rewrites_a_key_in_place(self):
		set_state(EXTENSION, {"theme": "dark"})
		set_state(EXTENSION, {"theme": "light"})

		self.assertEqual(get_state(EXTENSION), {"theme": "light"})
		self.assertEqual(self.rows(), ["theme"])

	def test_unset_drops_one_key_and_keeps_the_rest(self):
		set_state(EXTENSION, {"theme": "dark", "page": 2})

		unset_state(EXTENSION, "theme")

		self.assertEqual(get_state(EXTENSION), {"page": 2})

	def test_refuses_a_patch_that_is_not_an_object(self):
		"""Frappe's own type guard catches most of these before the method runs."""
		refusals = (frappe.ValidationError, frappe.exceptions.FrappeTypeError)
		for sent in ("dark", ["dark"], 3):
			with self.assertRaises(refusals, msg=repr(sent)):
				set_state(EXTENSION, sent)

	def test_the_cap_is_on_the_whole_store_and_not_one_key(self):
		"""A per-key cap would let an extension write a thousand small keys."""
		# each entry counts its one-letter key, and a value serializes to its
		# length plus the two quotes
		with patch("builder.extensions.state.MAX_STATE_BYTES", 40):
			set_state(EXTENSION, {"a": "x" * 15})
			set_state(EXTENSION, {"b": "x" * 15})

			with self.assertRaises(frappe.ValidationError):
				set_state(EXTENSION, {"c": "x" * 15})

	def test_the_cap_counts_key_names(self):
		with patch("builder.extensions.state.MAX_STATE_BYTES", 40):
			with self.assertRaises(frappe.ValidationError):
				set_state(EXTENSION, {"k" * 40: 1})

	def test_another_users_store_is_not_this_one(self):
		set_state(EXTENSION, {"theme": "dark"})
		theirs = make_user()
		make_installation(EXTENSION, user=theirs)

		frappe.set_user(theirs)
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertEqual(get_state(EXTENSION), {})

	def test_refuses_an_extension_this_user_has_not_installed(self):
		drop_installations("acme/absent")

		with self.assertRaises(frappe.PermissionError):
			get_state("acme/absent")

	def test_uninstall_takes_the_store_with_it(self):
		set_state(EXTENSION, {"theme": "dark"})

		self.installation.delete()

		self.assertEqual(frappe.get_all(STATE_DOCTYPE, filters={"state_key": "theme"}), [])

	def test_a_patch_that_is_not_an_object_is_refused_past_the_type_guard(self):
		for sent in ('"dark"', "[1]", "3"):
			with self.assertRaises(frappe.ValidationError, msg=sent):
				read_patch(sent)

	def test_adds_the_unique_index_once(self):
		on_doctype_update()
		on_doctype_update()

		self.assertTrue(frappe.db.has_index(TABLE, UNIQUE_INDEX))
