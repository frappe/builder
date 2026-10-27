import sys
from importlib import import_module
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase


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
