import os
from pathlib import Path
from unittest.mock import patch

import frappe
from babel.messages.extract import DEFAULT_KEYWORDS, extract_from_dir
from frappe.gettext.translate import get_method_map
from frappe.tests.utils import FrappeTestCase

from builder.www._builder import get_boot

FRONTEND_SRC = os.path.join("frontend", "src")


class TestI18n(FrappeTestCase):
	def test_frontend_strings_are_extractable(self):
		expected_locations = {
			"You do not have permission to access this page": {"frontend/src/router.ts"},
			"All Pages": {
				"frontend/src/components/DashboardHead.vue",
				"frontend/src/components/DashboardSidebar.vue",
			},
			"Select (v)": {"frontend/src/components/ToolbarItems/ModeSwitcher.vue"},
			'Are you sure you want to unpublish "{0}"? It will no longer be accessible on the website.': {
				"frontend/src/stores/pageStore.ts"
			},
		}

		for message, locations in self.extract_frontend_messages().items():
			if message in expected_locations:
				self.assertEqual(locations, expected_locations.pop(message), message)

		self.assertFalse(expected_locations, f"Not extracted: {sorted(expected_locations)}")

	def extract_frontend_messages(self) -> dict[str, set[str]]:
		"""Run the POT extractors over frontend/src only, the way generate_pot does."""
		app_path = frappe.get_pymodule_path("builder", "..")
		keywords = DEFAULT_KEYWORDS.copy()
		keywords["_lt"] = None

		def is_frontend_src(dirpath) -> bool:
			relative = os.path.relpath(dirpath, app_path)
			return relative == "." or FRONTEND_SRC.startswith(relative) or relative.startswith(FRONTEND_SRC)

		messages = {}
		for filename, _, message, _, _ in extract_from_dir(
			app_path,
			get_method_map("builder") + get_method_map("frappe"),
			directory_filter=is_frontend_src,
			keywords=keywords,
		):
			if message:
				messages.setdefault(message, set()).add(filename.replace("\\", "/"))
		return messages

	def test_catalogs_carry_no_in_context_placeholders(self):
		"""Crowdin's in-context pseudo language exports `crwdns...` ids instead of translations.

		They score as fully translated, so nothing upstream rejects them, and compiling one
		shows those ids across the whole editor.
		"""
		locale_dir = Path(frappe.get_app_path("builder")) / "locale"
		polluted = [po.name for po in locale_dir.glob("*.po") if "crwdns" in po.read_text(encoding="utf-8")]

		self.assertEqual(polluted, [], f"Crowdin in-context placeholders found in: {polluted}")

	def test_boot_carries_only_builder_translations(self):
		with patch("builder.www._builder.get_translations_from_apps", return_value={}) as from_apps:
			get_boot()

		from_apps.assert_called_once_with(frappe.local.lang, ["builder"])
