from unittest.mock import patch

import frappe
from frappe.gettext.translate import generate_pot
from frappe.tests.test_api import FrappeAPITestCase, make_request
from frappe.utils import get_test_client

from builder.api import get_translations


class TestI18n(FrappeAPITestCase):
	def test_generate_pot_includes_frontend_translations(self):
		expected_locations = {
			"You do not have permission to access this page": {"frontend/src/router.ts"},
			"All Pages": {
				"frontend/src/components/DashboardHead.vue",
				"frontend/src/components/DashboardSidebar.vue",
			},
			"Select (v)": {"frontend/src/components/BuilderToolbar.vue"},
			"Are you sure you want to unpublish {0}? It will no longer be accessible on the website.": {
				"frontend/src/stores/pageStore.ts"
			},
		}

		with patch("frappe.gettext.translate.write_catalog") as write_catalog:
			generate_pot("builder")

		write_catalog.assert_called_once()
		app, catalog = write_catalog.call_args.args
		self.assertEqual(app, "builder")

		for message, locations in expected_locations.items():
			catalog_message = catalog.get(message)
			self.assertIsNotNone(catalog_message, f"Missing message: {message}")
			actual_locations = {filename.replace("\\", "/") for filename, _ in catalog_message.locations}
			self.assertEqual(actual_locations, locations, message)

	def test_get_translations_uses_current_user_language(self):
		with (
			patch("frappe.translate.get_user_lang", return_value="de") as get_user_lang,
			patch(
				"frappe.translate.get_all_translations",
				return_value={"All Pages": "Alle Seiten"},
			) as get_all_translations,
		):
			self.assertEqual(get_translations(), {"All Pages": "Alle Seiten"})

		get_user_lang.assert_called_once_with()
		get_all_translations.assert_called_once_with("de")

	def test_get_translations_is_authenticated_and_get_only(self):
		self.assertIn(get_translations, frappe.whitelisted)
		self.assertNotIn(get_translations, frappe.guest_methods)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[get_translations], ["GET"])

	def test_authenticated_get_returns_translation_dictionary(self):
		with (
			patch("frappe.translate.get_user_lang", return_value="de"),
			patch(
				"frappe.translate.get_all_translations",
				return_value={"All Pages": "Alle Seiten"},
			),
		):
			response = self.get(
				self.method("builder.api.get_translations"),
				{"sid": self.sid},
			)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json["message"], {"All Pages": "Alle Seiten"})

	def test_guest_get_is_rejected(self):
		response = make_request(
			target=get_test_client(use_cookies=False).get,
			args=(self.method("builder.api.get_translations"),),
		)

		self.assertEqual(response.status_code, 403)

	def test_authenticated_post_is_rejected(self):
		response = self.post(
			self.method("builder.api.get_translations"),
			{"sid": self.sid},
		)

		self.assertEqual(response.status_code, 403)
