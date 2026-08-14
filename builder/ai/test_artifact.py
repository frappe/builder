from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.artifact import brief_image_parts, image_url_resolves

PUBLIC = "https://cdn.example.com/hero.png"
PRIVATE = "https://internal.example.com/hero.png"


class Response:
	def __init__(self, status_code=200):
		self.status_code = status_code
		self.ok = status_code < 400

	def close(self):
		pass


def responding(status_code=200):
	return patch("builder.ai.agent.artifact.requests.head", return_value=Response(status_code))


def allowing():
	return patch("builder.ai.agent.artifact.assert_not_private_url")


def blocking():
	return patch("builder.ai.agent.artifact.assert_not_private_url", side_effect=Exception("private"))


class TestImageUrlResolves(FrappeTestCase):
	def test_accepts_a_reachable_url(self):
		with allowing(), responding(200):
			self.assertTrue(image_url_resolves(PUBLIC))

	def test_rejects_a_missing_url(self):
		with allowing(), responding(404):
			self.assertFalse(image_url_resolves(PUBLIC))

	def test_accepts_a_redirect_without_following_it(self):
		with allowing(), responding(302) as head:
			self.assertTrue(image_url_resolves(PUBLIC))

		self.assertFalse(head.call_args.kwargs["allow_redirects"])

	def test_rejects_a_private_url(self):
		with blocking(), responding(200) as head:
			self.assertFalse(image_url_resolves(PRIVATE))

		head.assert_not_called()

	def test_falls_back_to_get_when_head_is_refused(self):
		with (
			allowing(),
			responding(405),
			patch("builder.ai.agent.artifact.requests.get", return_value=Response(200)) as get,
		):
			self.assertTrue(image_url_resolves(PUBLIC))

		self.assertFalse(get.call_args.kwargs["allow_redirects"])


class TestBriefImageParts(FrappeTestCase):
	def test_attaches_a_reachable_marker(self):
		with allowing(), responding(200):
			parts = brief_image_parts(f"HERO IMAGE: {PUBLIC}")

		self.assertEqual(parts, [{"type": "image_url", "image_url": {"url": PUBLIC}}])

	def test_skips_a_private_marker(self):
		with blocking(), responding(200):
			parts = brief_image_parts(f"REFERENCE IMAGE: {PRIVATE}")

		self.assertEqual(parts, [])

	def test_stops_at_the_attachment_limit(self):
		brief = "\n".join(f"HERO IMAGE: https://cdn.example.com/{i}.png" for i in range(4))
		with allowing(), responding(200):
			parts = brief_image_parts(brief)

		self.assertEqual(len(parts), 2)
