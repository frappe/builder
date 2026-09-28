from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.web import (
	MAX_RESEARCH_PER_TURN,
	MAX_URL_READS_PER_TURN,
	extract_title,
	html_to_text,
	run_read_url,
	run_research,
)


def ctx(**overrides):
	defaults = {
		"web_read_count": 0,
		"research_count": 0,
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


class TestReadUrl(FrappeTestCase):
	def test_refuses_private_addresses(self):
		out = run_read_url(ctx(), {"url": "http://127.0.0.1:8000/admin"})

		self.assertIn("FAILED", out)
		self.assertIn("private or internal", out)

	def test_refuses_non_http_schemes(self):
		self.assertIn("FAILED", run_read_url(ctx(), {"url": "ftp://example.com/file"}))

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


class TestPinnedUrl(FrappeTestCase):
	def test_dials_the_ip_and_keeps_the_host_header(self):
		from builder.ai.agent.tools.web import pinned_url

		self.assertEqual(
			pinned_url("https://example.com/a?b=1", "93.184.216.34"),
			("https://93.184.216.34/a?b=1", "example.com"),
		)

	def test_brackets_ipv6_and_keeps_ports(self):
		from builder.ai.agent.tools.web import pinned_url

		self.assertEqual(
			pinned_url("http://example.com:8080/x", "2606:2800:220:1::1"),
			("http://[2606:2800:220:1::1]:8080/x", "example.com:8080"),
		)
