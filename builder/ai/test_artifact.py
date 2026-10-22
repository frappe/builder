from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.artifact import brief_image_parts, image_url_resolves, reference_geometry

PUBLIC = "https://cdn.example.com/hero.png"
PRIVATE = "https://internal.example.com/hero.png"


class Response:
	def __init__(self, status_code=200):
		self.status_code = status_code
		self.ok = status_code < 400

	def close(self):
		pass


def responding(status_code=200):
	return patch(
		"builder.ai.agent.artifact.public_session",
		**{"return_value.head.return_value": Response(status_code)},
	)


def blocking():
	return patch(
		"builder.ai.agent.artifact.public_session",
		**{"return_value.head.side_effect": frappe.PermissionError("private")},
	)


class TestImageUrlResolves(FrappeTestCase):
	def test_accepts_a_reachable_url(self):
		with responding(200):
			self.assertTrue(image_url_resolves(PUBLIC))

	def test_rejects_a_missing_url(self):
		with responding(404):
			self.assertFalse(image_url_resolves(PUBLIC))

	def test_accepts_a_redirect_without_following_it(self):
		with responding(302) as session:
			self.assertTrue(image_url_resolves(PUBLIC))

		self.assertFalse(session.return_value.head.call_args.kwargs["allow_redirects"])

	def test_rejects_a_private_url(self):
		with blocking():
			self.assertFalse(image_url_resolves(PRIVATE))

	def test_falls_back_to_get_when_head_is_refused(self):
		with responding(405) as session:
			session.return_value.get.return_value = Response(200)
			self.assertTrue(image_url_resolves(PUBLIC))

		self.assertFalse(session.return_value.get.call_args.kwargs["allow_redirects"])


class TestBriefImageParts(FrappeTestCase):
	def test_attaches_a_reachable_marker(self):
		with responding(200):
			parts = brief_image_parts(f"HERO IMAGE: {PUBLIC}")

		self.assertEqual(parts, [{"type": "image_url", "image_url": {"url": PUBLIC}}])

	def test_skips_a_private_marker(self):
		with blocking():
			parts = brief_image_parts(f"REFERENCE IMAGE: {PRIVATE}")

		self.assertEqual(parts, [])

	def test_stops_at_the_attachment_limit(self):
		brief = "\n".join(f"HERO IMAGE: https://cdn.example.com/{i}.png" for i in range(4))
		with responding(200):
			parts = brief_image_parts(brief)

		self.assertEqual(len(parts), 2)


class TestReferenceGeometry(FrappeTestCase):
	def test_no_reads_yields_nothing(self):
		self.assertEqual(reference_geometry(SimpleNamespace(reference_reads=[])), "")

	def test_single_read_stays_unlabelled(self):
		out = reference_geometry(SimpleNamespace(reference_reads=["Page A: geometry"]))
		self.assertIn("Page A: geometry", out)
		self.assertNotIn("PRIMARY REFERENCE", out)

	def test_first_read_is_primary_and_the_rest_secondary(self):
		out = reference_geometry(SimpleNamespace(reference_reads=["Page A: geometry", "Page B: geometry"]))
		self.assertLess(out.index("PRIMARY REFERENCE"), out.index("Page A: geometry"))
		self.assertLess(out.index("SECONDARY REFERENCE"), out.index("Page B: geometry"))
		self.assertEqual(out.count("PRIMARY REFERENCE"), 1)
