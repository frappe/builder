import json
from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.web import (
	MAX_RESEARCH_PER_TURN,
	MAX_URL_READS_PER_TURN,
	extract_title,
	html_to_text,
	pick_fields,
	run_read_url,
	run_research,
)


def ctx(**overrides):
	defaults = {
		"web_read_count": 0,
		"research_count": 0,
		"web_sources": [],
		"loop_model": "openrouter/test-model",
		"model": "openrouter/test-model",
		"api_key": "key",
	}
	return SimpleNamespace(**{**defaults, **overrides})


class TestHtmlToText(FrappeTestCase):
	def test_strips_code_and_keeps_copy(self):
		markup = "<html><script>var x=1;</script><style>.a{}</style><h1>Bakery</h1><p>Since 1―982</p></html>"

		out = html_to_text(markup)

		self.assertIn("Bakery", out)
		self.assertNotIn("var x", out)
		self.assertNotIn(".a{}", out)

	def test_block_tags_become_line_breaks(self):
		out = html_to_text("<p>one</p><p>two</p>")

		self.assertEqual(out, "one\ntwo")

	def test_unescapes_entities_and_reads_title(self):
		self.assertEqual(html_to_text("<p>Fish &amp; Chips</p>"), "Fish & Chips")
		self.assertEqual(extract_title("<title>Caf&eacute; Nine</title>"), "Café Nine")


def fetched(body: bytes, content_type: str = "text/html", url: str = "https://example.com/"):
	"""Every fetch answers 200 with `body`, without touching the network."""
	page = SimpleNamespace(
		headers={"content-type": content_type},
		status_code=200,
		url=url,
		encoding="utf-8",
		iter_content=lambda **kwargs: iter([body]),
	)
	session = SimpleNamespace(get=lambda *args, **kwargs: page)
	return patch("builder.ai.agent.tools.web.public_session", return_value=session)


SPEAKERS = {
	"count": 2,
	"results": [
		{"fullname": "Ada", "biography": "x" * 9000, "avatar_url": "https://a.png", "answers": []},
		{"fullname": "Lin", "biography": "y" * 9000, "avatar_url": None, "answers": []},
	],
}


class TestPickFields(FrappeTestCase):
	def test_keeps_named_keys_at_any_depth(self):
		picked = pick_fields(SPEAKERS, {"fullname", "avatar_url"})

		self.assertEqual(
			picked,
			{
				"results": [
					{"fullname": "Ada", "avatar_url": "https://a.png"},
					{"fullname": "Lin", "avatar_url": None},
				]
			},
		)

	def test_nothing_matched_is_none(self):
		self.assertIsNone(pick_fields(SPEAKERS, {"title"}))


class TestReadUrl(FrappeTestCase):
	def test_refuses_private_addresses(self):
		out = run_read_url(ctx(), {"url": "http://127.0.0.1:8000/admin"})

		self.assertIn("FAILED", out)
		self.assertIn("private or internal", out)

	def test_reads_a_public_page(self):
		with fetched(b"<title>Example</title><p>Hello there</p>"):
			out = run_read_url(ctx(), {"url": "https://example.com"})

		self.assertTrue(out.startswith("Read https://example.com/"))
		self.assertIn("Hello there", out)

	def test_lists_the_data_links_a_page_declares(self):
		markup = (
			b'<link rel="alternate" hreflang="de" href="/de/">'
			b'<link rel="alternate" type="application/json" title="Event API" href="/api/v1/events/x/">'
			b"<p>Speakers</p>"
		)
		with fetched(markup, url="https://events.example.com/x/speakers/"):
			out = run_read_url(ctx(), {"url": "https://events.example.com/x/speakers/"})

		self.assertIn(
			"Data links the page declares:\n- application/json 'Event API': https://events.example.com/api/v1/events/x/",
			out,
		)
		self.assertNotIn("/de/", out)

	def test_refuses_non_http_schemes(self):
		self.assertIn("FAILED", run_read_url(ctx(), {"url": "ftp://example.com/file"}))

	def test_fields_fit_a_long_json_list_in_one_read(self):
		context = ctx()
		url = "https://api.example.com/speakers"
		with fetched(json.dumps(SPEAKERS).encode(), "application/json", url):
			out = run_read_url(context, {"url": url, "fields": "fullname, avatar_url"})

		self.assertIn('{"results":[{"fullname":"Ada","avatar_url":"https://a.png"}', out)
		self.assertNotIn("truncated", out)
		self.assertEqual(context.web_sources, [{"url": url, "fields": ["fullname", "avatar_url"]}])

	def test_truncated_json_points_at_fields(self):
		with fetched(json.dumps(SPEAKERS).encode(), "application/json"):
			out = run_read_url(ctx(), {"url": "https://example.com"})

		self.assertTrue(out.endswith("(truncated; pass `fields` to keep only the keys you need)"))

	def test_fields_that_match_nothing_say_so(self):
		with fetched(json.dumps(SPEAKERS).encode(), "application/json"):
			out = run_read_url(ctx(), {"url": "https://example.com", "fields": ["title"]})

		self.assertIn("no title key in this JSON", out)

	def test_fields_on_broken_json_return_the_body(self):
		with fetched(b'{"results": [', "application/json"):
			out = run_read_url(ctx(), {"url": "https://example.com", "fields": ["title"]})

		self.assertIn('{"results": [', out)

	def test_rereading_a_source_records_it_once(self):
		context = ctx()
		with fetched(b"<p>Hello</p>"):
			run_read_url(context, {"url": "https://example.com"})
			run_read_url(context, {"url": "https://example.com"})

		self.assertEqual(context.web_sources, [{"url": "https://example.com/"}])

	def test_caps_reads_per_turn(self):
		out = run_read_url(ctx(web_read_count=MAX_URL_READS_PER_TURN), {"url": "https://example.com"})

		self.assertIn("limit reached", out)


class TestResearch(FrappeTestCase):
	def test_uses_the_online_variant_of_the_loop_model(self):
		with patch("builder.ai.llm.complete", return_value="- Finding (https://src)") as complete:
			out = run_research(ctx(), {"question": "What are Café Nine's opening hours?"})

		self.assertEqual(out, "- Finding (https://src)")
		self.assertTrue(complete.call_args.args[0].endswith(":online"))

	def test_falls_back_helpfully_off_openrouter(self):
		out = run_research(ctx(loop_model="codex/gpt-x", model="codex/gpt-x"), {"question": "q"})

		self.assertIn("FAILED", out)
		self.assertIn("read_url", out)

	def test_caps_research_per_turn(self):
		out = run_research(ctx(research_count=MAX_RESEARCH_PER_TURN), {"question": "q"})

		self.assertIn("limit reached", out)
