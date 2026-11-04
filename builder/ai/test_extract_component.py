from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.components import run_extract_component


class TestExtractComponent(FrappeTestCase):
	def test_the_component_is_committed_before_the_editor_hears_of_it(self):
		events = []
		header = {
			"blockId": "header",
			"element": "header",
			"children": [{"blockId": "logo", "element": "p", "innerHTML": "Acme"}],
		}
		ctx = SimpleNamespace(
			tree=SimpleNamespace(root={"blockId": "root", "element": "div", "children": [header]}),
			queue_client_op=lambda op: events.append(op["tool_name"]),
		)

		with patch.object(frappe.db, "commit", side_effect=lambda: events.append("commit")):
			result = run_extract_component(ctx, {"block_id": "header", "component_name": "Acme Header"})

		self.assertIn("Extracted 'Acme Header'", result)
		self.assertEqual(events, ["commit", "set_page_blocks"])
