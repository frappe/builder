import json

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.data import CODE_FIELD_CAP, get_document


def read(request: dict):
	return json.loads(get_document(None, request))


class TestGetDocument(FrappeTestCase):
	def test_returns_code_fields_nearly_whole(self):
		style = "\n".join(f".rule-{i} {{ color: red; }}" for i in range(200))
		frappe.db.set_single_value("Builder Settings", "style", style)

		out = read({"doctype": "Builder Settings", "fields": ["style"]})

		self.assertGreater(len(out["style"]), 1001)  # the old generic cap shredded these
		self.assertLessEqual(len(out["style"]), CODE_FIELD_CAP + 1)

	def test_flags_a_field_that_does_not_exist(self):
		out = read({"doctype": "Builder Settings", "fields": ["no_such_field"]})

		self.assertIn("no field 'no_such_field'", out["no_such_field"])
