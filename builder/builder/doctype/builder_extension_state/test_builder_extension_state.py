# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_table_name

from builder.builder.doctype.builder_extension_state.builder_extension_state import (
	UNIQUE_INDEX,
	on_doctype_update,
)
from builder.builder.tests.extension_fixtures import (
	drop_installations,
	make_installation,
	make_page_reader,
	make_user,
)
from builder.extensions import state
from builder.extensions.state import STATE_DOCTYPE, get_changes, get_state, set_state, unset_state

EXTENSION = "acme/remembers"
real_write_row = state.write_row


class TestExtensionState(FrappeTestCase):
	"""Tests the state of one extension for one user."""

	def setUp(self):
		drop_installations(EXTENSION)
		self.installation = make_installation(EXTENSION)

	def rows(self):
		return frappe.get_all(STATE_DOCTYPE, filters={"installation": self.installation.name}, pluck="name")

	def test_answers_with_nothing_before_anything_is_stored(self):
		self.assertEqual(get_state(EXTENSION), {})

	def test_stores_and_reads_a_value_back(self):
		set_state(EXTENSION, {"theme": "dark"})

		self.assertEqual(get_state(EXTENSION), {"theme": "dark"})

	def test_merges_and_never_removes_what_a_call_leaves_unmentioned(self):
		set_state(EXTENSION, {"theme": "dark"})
		set_state(EXTENSION, {"page": 2})

		self.assertEqual(get_state(EXTENSION), {"theme": "dark", "page": 2})

	def test_one_row_holds_the_whole_store(self):
		set_state(EXTENSION, {"theme": "dark", "page": 2})
		set_state(EXTENSION, {"theme": "light"})

		self.assertEqual(get_state(EXTENSION), {"theme": "light", "page": 2})
		self.assertEqual(len(self.rows()), 1)

	def test_many_keys_take_as_few_queries_as_one(self):
		"""Counts the queries: the installation, the locked row and one update."""
		set_state(EXTENSION, {"first": 1})

		with self.assertQueryCount(3):
			set_state(EXTENSION, {str(number): number for number in range(200)})

		self.assertEqual(len(get_state(EXTENSION)), 201)

	def test_a_first_write_that_loses_the_race_merges_into_the_winner(self):
		"""Two frames have no row to lock. So MariaDB stops one write with a deadlock."""
		attempts = []

		def lose_the_first_attempt(*args):
			attempts.append(args)
			if len(attempts) == 1:
				real_write_row(EXTENSION, self.installation.name, None, {"theme": "dark"})
				raise frappe.QueryDeadlockError
			real_write_row(*args)

		with (
			patch.object(state, "write_row", lose_the_first_attempt),
			patch.object(frappe.db, "rollback") as rollback,
			patch.object(frappe.db, "transaction_writes", 0),
		):
			set_state(EXTENSION, {"page": 2})

		rollback.assert_called_once()
		self.assertEqual(get_state(EXTENSION), {"theme": "dark", "page": 2})
		self.assertEqual(len(self.rows()), 1)

	def test_retries_a_lost_race_only_once(self):
		with (
			patch.object(state, "write_row", side_effect=frappe.QueryDeadlockError),
			patch.object(frappe.db, "rollback") as rollback,
			patch.object(frappe.db, "transaction_writes", 0),
		):
			with self.assertRaises(frappe.QueryDeadlockError):
				set_state(EXTENSION, {"page": 2})

		rollback.assert_called_once()

	def test_a_lost_race_after_earlier_writes_is_not_retried(self):
		"""A rollback would remove the earlier writes. So the error goes to the caller."""
		with (
			patch.object(state, "write_row", side_effect=frappe.QueryDeadlockError),
			patch.object(frappe.db, "rollback") as rollback,
			patch.object(frappe.db, "transaction_writes", 1),
		):
			with self.assertRaises(frappe.QueryDeadlockError):
				set_state(EXTENSION, {"page": 2})

		rollback.assert_not_called()

	def test_unset_drops_one_key_and_keeps_the_rest(self):
		set_state(EXTENSION, {"theme": "dark", "page": 2})

		unset_state(EXTENSION, "theme")

		self.assertEqual(get_state(EXTENSION), {"page": 2})

	def test_refuses_changes_that_are_not_an_object(self):
		"""Frappe checks most of these types before the method runs."""
		refusals = (frappe.ValidationError, frappe.exceptions.FrappeTypeError)
		for sent in ("dark", ["dark"], 3):
			with self.assertRaises(refusals, msg=repr(sent)):
				set_state(EXTENSION, sent)

	def test_the_cap_is_on_the_whole_store_and_not_one_key(self):
		"""The limit is for all keys. A limit for each key allows many small keys."""
		# The JSON is 24 characters for one key, 48 for two and 72 for three.
		with patch("builder.extensions.state.MAX_STATE_BYTES", 50):
			set_state(EXTENSION, {"a": "x" * 15})
			set_state(EXTENSION, {"b": "x" * 15})

			with self.assertRaises(frappe.ValidationError):
				set_state(EXTENSION, {"c": "x" * 15})

	def test_the_cap_counts_key_names(self):
		with patch("builder.extensions.state.MAX_STATE_BYTES", 40):
			with self.assertRaises(frappe.ValidationError):
				set_state(EXTENSION, {"k" * 40: 1})

	def test_another_users_store_is_not_this_one(self):
		"""The installation belongs to the site. The state belongs to each user."""
		set_state(EXTENSION, {"theme": "dark"})

		frappe.set_user(make_user())
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertEqual(get_state(EXTENSION), {})

	def test_two_users_store_one_key_separately(self):
		set_state(EXTENSION, {"theme": "dark"})
		frappe.set_user(make_user())
		self.addCleanup(frappe.set_user, "Administrator")

		set_state(EXTENSION, {"theme": "light"})
		self.assertEqual(get_state(EXTENSION), {"theme": "light"})

		frappe.set_user("Administrator")
		self.assertEqual(get_state(EXTENSION), {"theme": "dark"})

	def test_a_user_without_a_manager_role_stores_and_drops_keys(self):
		"""Only a System Manager has the doctype permission. The checks still let this user in."""
		frappe.set_user(make_page_reader(self))
		self.addCleanup(frappe.set_user, "Administrator")

		set_state(EXTENSION, {"theme": "dark", "page": 2})
		unset_state(EXTENSION, "theme")

		self.assertEqual(get_state(EXTENSION), {"page": 2})

	def test_only_a_system_manager_reaches_the_doctype_directly(self):
		"""The REST routes do not run the checks, the size limit or the session user."""
		self.assertFalse(frappe.has_permission(STATE_DOCTYPE, "read", user=make_user()))

	def test_refuses_an_extension_this_user_has_not_installed(self):
		drop_installations("acme/absent")

		with self.assertRaises(frappe.PermissionError):
			get_state("acme/absent")

	def test_uninstall_takes_the_store_with_it(self):
		set_state(EXTENSION, {"theme": "dark"})

		self.installation.delete()

		self.assertEqual(self.rows(), [])

	def test_changes_that_are_not_an_object_are_refused_past_the_type_guard(self):
		for sent in ('"dark"', "[1]", "3"):
			with self.assertRaises(frappe.ValidationError, msg=sent):
				get_changes(sent)

	def test_adds_the_unique_index_once(self):
		on_doctype_update()
		on_doctype_update()

		self.assertTrue(frappe.db.has_index(get_table_name(STATE_DOCTYPE), UNIQUE_INDEX))
