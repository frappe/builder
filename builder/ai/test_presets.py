import sys
from importlib import import_module
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.llm import NO_KEY
from builder.ai.presets import install_preset, verify_key

PRESET = {
	"name": "Test Preset",
	"route_prefix": "test-preset",
	"litellm_provider": "openai",
	"api_base": "https://preset.test/v1",
	"models": [
		("vendor/main", "Main", "", True),
		("vendor/extra", "Extra", "", False),
	],
}


class TestInstallPreset(FrappeTestCase):
	def tearDown(self):
		frappe.db.delete("Builder AI Model", {"provider": PRESET["name"]})
		frappe.delete_doc("Builder AI Provider", PRESET["name"], force=True, ignore_permissions=True)

	def enabled(self, model_id: str):
		return frappe.db.get_value("Builder AI Model", f"test-preset/{model_id}", "enabled")

	def test_the_rest_of_the_shortlist_lands_switched_off(self):
		install_preset(PRESET, "key", "", ["vendor/main"])
		self.assertEqual(self.enabled("vendor/main"), 1)
		self.assertEqual(self.enabled("vendor/extra"), 0)

	def test_reconnecting_leaves_a_switched_on_extra_alone(self):
		install_preset(PRESET, "key", "", ["vendor/main"])
		frappe.db.set_value("Builder AI Model", "test-preset/vendor/extra", "enabled", 1)
		install_preset(PRESET, "key", "", ["vendor/main"])
		self.assertEqual(self.enabled("vendor/extra"), 1)


class TestVerifyKey(FrappeTestCase):
	def test_a_keyless_gateway_is_called_with_the_placeholder_key(self):
		with patch("litellm.completion") as completion:
			result = verify_key({**PRESET, "id": "test-preset"}, "", "", "vendor/main")
		self.assertTrue(result["success"])
		self.assertEqual(completion.call_args.kwargs["api_key"], NO_KEY)


class TestMigrateWithoutLitellm(FrappeTestCase):
	def test_the_model_upgrade_patch_loads_when_litellm_cannot(self):
		with patch.dict(sys.modules, {"litellm": None}):
			for module in (
				"builder.builder.patches.upgrade_ai_models",
				"builder.ai.presets",
				"builder.ai.llm",
			):
				sys.modules.pop(module, None)
			import_module("builder.builder.patches.upgrade_ai_models")
