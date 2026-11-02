"""Regression boundaries left open by the initial review implementation."""

import logging
import unittest
from unittest.mock import MagicMock, patch

import frappe

with patch.object(frappe, "logger", return_value=logging.getLogger(__name__)):
	from builder.ai.page_writer import persist_page, validate_page_candidate


class TestCandidateCompleteness(unittest.TestCase):
	def test_valid_empty_generation_cannot_replace_existing_draft(self):
		with patch.object(frappe, "db", MagicMock()) as db:
			with self.assertRaisesRegex(ValueError, "no content"):
				persist_page("fixture", "el: div\nc:\n")
			db.set_value.assert_not_called()

	def test_one_purpose_page_does_not_need_arbitrary_sections(self):
		validate_page_candidate({"blockId": "root", "element": "h1", "innerHTML": "Back soon"})

	def test_bound_content_is_meaningful_without_static_copy(self):
		validate_page_candidate({"blockId": "root", "dynamicValues": [{"key": "title"}]})

	def test_duplicate_ids_do_not_reach_the_editor(self):
		with self.assertRaisesRegex(ValueError, "Duplicate"):
			validate_page_candidate(
				{"blockId": "root", "children": [{"blockId": "root", "innerHTML": "Oops"}]}
			)
