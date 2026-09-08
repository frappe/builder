from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.api import create_page_from_bundle, duplicate_page, identify_persona
from builder.utils import count_blocks

CAPTURE = "builder.builder.doctype.builder_page.builder_page.capture"
IDENTIFY = "frappe.utils.telemetry.pulse.client.identify"

ROOT = {"element": "div"}
ROOT_WITH_CHILD = {"element": "div", "children": [{"element": "p"}]}


def captured(capture, event):
	return [call.kwargs["properties"] for call in capture.call_args_list if call.args[0] == event]


def new_page(**fields):
	return frappe.get_doc({"doctype": "Builder Page", "page_title": "Telemetry", **fields}).insert()


class TestPageLifecycleEvents(FrappeTestCase):
	def test_counts_a_legacy_single_root_block(self):
		self.assertEqual(count_blocks(ROOT_WITH_CHILD), 2)
		self.assertEqual(count_blocks(None), 0)

	def test_created_event_identifies_the_page(self):
		with patch(CAPTURE) as capture:
			page = new_page(draft_blocks=[ROOT_WITH_CHILD])

		[props] = captured(capture, "builder_page_created")
		self.assertEqual(props["page"], page.name)
		self.assertEqual(props["block_count"], 2)
		self.assertEqual(props["source"], "import")
		self.assertIsNone(props["template_page"])

	def test_page_with_only_a_root_block_is_blank(self):
		with patch(CAPTURE) as capture:
			new_page(draft_blocks=[ROOT])

		[props] = captured(capture, "builder_page_created")
		self.assertEqual(props["source"], "blank")

	def test_template_and_duplicate_sources(self):
		bundle = {"page": {"page_title": "From Template", "blocks": [ROOT_WITH_CHILD]}}
		with patch(CAPTURE) as capture:
			name = create_page_from_bundle(bundle, template_page="hub-page")
			duplicate_page(name)

		from_template, duplicated = captured(capture, "builder_page_created")
		self.assertEqual(from_template["source"], "template")
		self.assertEqual(from_template["template_page"], "hub-page")
		self.assertEqual(duplicated["source"], "duplicate")
		self.assertIsNone(duplicated["template_page"])

	def test_publish_event_marks_the_first_publish(self):
		page = new_page(draft_blocks=[ROOT_WITH_CHILD], page_data_script="data.update({})")
		with patch(CAPTURE) as capture:
			page.publish()
			page.publish()

		first, second = captured(capture, "builder_page_published")
		self.assertEqual(first["page"], page.name)
		self.assertTrue(first["is_first_publish"])
		self.assertFalse(second["is_first_publish"])
		self.assertEqual(first["block_count"], 2)
		self.assertTrue(first["has_data_script"])
		self.assertFalse(first["has_client_script"])
		self.assertGreaterEqual(first["seconds_since_created"], 0)

	def test_republishing_an_unpublished_page_is_not_a_first_publish(self):
		page = new_page(draft_blocks=[ROOT])
		page.publish()
		page.published = 0
		page.save()
		with patch(CAPTURE) as capture:
			page.publish()

		[props] = captured(capture, "builder_page_published")
		self.assertFalse(props["is_first_publish"])

	def test_unpublish_event_fires_on_a_plain_field_update(self):
		page = new_page(draft_blocks=[ROOT])
		page.publish()
		with patch(CAPTURE) as capture:
			page.published = 0
			page.save()

		self.assertEqual(captured(capture, "builder_page_unpublished"), [{"page": page.name}])

	def test_creating_an_unpublished_page_is_not_an_unpublish(self):
		with patch(CAPTURE) as capture:
			new_page(draft_blocks=[ROOT])

		self.assertEqual(captured(capture, "builder_page_unpublished"), [])


class TestIdentifyPersona(FrappeTestCase):
	def test_sends_the_answers_to_the_site_profile(self):
		with patch(IDENTIFY) as identify:
			identify_persona(role="designer", use_case="portfolio", source="search")

		identify.assert_called_once_with(
			{"builder_role": "designer", "builder_use_case": "portfolio", "builder_source": "search"}
		)

	def test_a_skipped_survey_is_not_sent(self):
		with patch(IDENTIFY) as identify:
			identify_persona()

		identify.assert_not_called()
