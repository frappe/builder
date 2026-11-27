"""Builder's AI on Anthropic's own API: the requests it makes there are ones Claude Opus 5.5 takes, an
Anthropic site config key goes to api.anthropic.com only, and a refusal ends a turn in plain words."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import llm, test_presets
from builder.ai.agent.loop import AgentRunner
from builder.ai.models import GatewayListing, ModelRegistry, current_claude_models
from builder.ai.presets import ADOPTED_DEFAULT_KEY, sync_site_provider
from builder.ai.session import AISession
from builder.ai.site_key import ANTHROPIC_API, REDACTED, Charge, SiteAIKey, Usage
from builder.ai.test_page_changes import chunk, heading, make_page, texts, tool_call
from builder.ai.test_presets import SITE_KEY, site_config

OPUS = "anthropic/claude-opus-5-5"
ANTHROPIC_KEY = "sk-ant-operator-0123456789"
ANTHROPIC_SITE_KEY = {"ai_keys": [{"provider": "anthropic", "api_key": ANTHROPIC_KEY}]}
REFUSED_BY_OPUS_5_5 = ("temperature", "top_p", "top_k")


def claude(model_id, line, created, context=1_000_000, image=True, **extra):
	"""An entry as Anthropic's /v1/models lists it."""
	return {
		"type": "model",
		"id": model_id,
		"display_name": f"Display name of {model_id}",
		"created_at": created,
		"line": line,
		"max_input_tokens": context,
		"max_tokens": 128_000,
		"capabilities": {"image_input": {"supported": image}},
		"lifecycle": "active",
		"deprecated_at": None,
		"retires_at": None,
		**extra,
	}


LISTED = [
	claude("claude-fable-5-2", "fable", "2026-11-09T18:30:00Z"),
	claude("claude-haiku-5-5", "haiku", "2026-10-07T18:00:00Z"),
	claude("claude-sonnet-5-5", "sonnet", "2026-09-28T00:00:00Z"),
	claude("claude-opus-5-5", "opus", "2026-09-21T16:24:00Z"),
	claude("claude-fable-5-1", "fable", "2026-08-28T00:00:00Z"),
	claude("claude-opus-5", "opus", "2026-07-24T00:00:00Z"),
	claude("claude-opus-4-8", "opus", "2026-05-28T00:00:00Z"),
	claude("claude-sonnet-4-5-20250929", "sonnet", "2025-09-29T00:00:00Z", context=200_000),
]


def listing_response(entries=LISTED):
	response = MagicMock()
	response.json.return_value = {"data": entries, "has_more": False}
	return response


class TestAnthropicParams(FrappeTestCase):
	"""What each of Builder's calls asks of Anthropic's own API."""

	def test_no_call_sends_a_sampling_knob_and_every_call_names_its_effort(self):
		calls = {
			"agent round": (llm.TASK_PARAMS["agent"], "medium"),
			"page generation": (llm.TASK_PARAMS["complex"], "high"),
			"chat title": ({"max_tokens": 24, "temperature": 0.3}, "low"),
			"key check": ({"max_tokens": 10}, "low"),
			"picked effort": (llm.Effort("xhigh").params("agent"), "xhigh"),
			"everything else": (llm.TASK_PARAMS["clarify"] | {"top_p": 0.9, "top_k": 5}, "low"),
		}
		for name, (params, effort) in calls.items():
			with self.subTest(name):
				sent = llm.patch_params_for_provider(OPUS, params)
				self.assertFalse(set(REFUSED_BY_OPUS_5_5) & set(sent))
				self.assertNotIn("reasoning_effort", sent)
				self.assertEqual(sent["thinking"], {"type": "adaptive", "display": "summarized"})
				self.assertEqual(sent["output_config"], {"effort": effort})
				# thinking counts against max_tokens, so even a title has room to think and answer
				self.assertGreaterEqual(sent["max_tokens"], llm.MIN_CLAUDE_MAX_TOKENS)

	def test_the_tiers_keep_their_own_parameters(self):
		llm.patch_params_for_provider(OPUS, llm.TASK_PARAMS["agent"])
		self.assertEqual(llm.TASK_PARAMS["agent"]["temperature"], 0.7)

	def test_a_claude_older_than_adaptive_thinking_keeps_its_thinking_budget(self):
		sent = llm.patch_params_for_provider("anthropic/claude-sonnet-4-5", llm.TASK_PARAMS["complex"])
		self.assertEqual(sent["reasoning_effort"], "high")
		self.assertNotIn("temperature", sent)
		self.assertNotIn("thinking", sent)

	def test_a_conversation_never_ends_on_the_assistant(self):
		for messages, added in (
			([{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Applied."}], True),
			([{"role": "user", "content": "hi"}], False),
			([{"role": "assistant", "content": None, "tool_calls": [{"id": "t"}]}], False),
		):
			with self.subTest(messages=messages):
				prepared = [dict(m) for m in messages]
				llm.prepare_request(OPUS, prepared, {})
				self.assertEqual(prepared[-1] == {"role": "user", "content": "Continue."}, added)
		gateway = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Applied."}]
		llm.prepare_request("openai/gpt-6-luna", gateway, {})
		self.assertEqual(gateway[-1]["role"], "assistant")


class CapturedAnthropic:
	"""A local stand-in for api.anthropic.com that records what litellm sends it."""

	REPLY: ClassVar[dict] = {
		"id": "msg_test",
		"type": "message",
		"role": "assistant",
		"model": "claude-opus-5-5",
		"content": [{"type": "text", "text": "Pricing Plans"}],
		"stop_reason": "end_turn",
		"usage": {"input_tokens": 12, "output_tokens": 3},
	}

	def __enter__(self):
		self.bodies = []
		captured = self.bodies
		reply = json.dumps(self.REPLY).encode()

		class Handler(BaseHTTPRequestHandler):
			def do_POST(self):
				captured.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
				self.send_response(200)
				self.send_header("content-type", "application/json")
				self.send_header("content-length", str(len(reply)))
				self.end_headers()
				self.wfile.write(reply)

			def log_message(self, *args):
				pass

		self.server = HTTPServer(("127.0.0.1", 0), Handler)
		threading.Thread(target=self.server.serve_forever, daemon=True).start()
		self.route = patch(
			"builder.ai.llm.route",
			return_value=(OPUS, {"api_base": f"http://127.0.0.1:{self.server.server_port}"}, "test-key"),
		)
		self.route.start()
		return self

	def __exit__(self, *exc):
		self.route.stop()
		self.server.shutdown()
		self.server.server_close()


class TestWhatLitellmSends(FrappeTestCase):
	"""The request bodies themselves, as litellm's native Anthropic route writes them."""

	TOOLS: ClassVar[list] = [
		{"type": "function", "function": {"name": "read_page", "parameters": {"type": "object"}}}
	]

	def assert_opus_5_5_takes(self, body, effort):
		self.assertFalse(set(REFUSED_BY_OPUS_5_5) & set(body))
		self.assertEqual(body["thinking"], {"type": "adaptive", "display": "summarized"})
		self.assertEqual(body["output_config"], {"effort": effort})
		self.assertNotIn(body.get("tool_choice", {}).get("type"), ("any", "tool"))
		self.assertEqual(body["messages"][-1]["role"], "user")

	def test_an_agent_round(self):
		with CapturedAnthropic() as api:
			llm.complete_with_tools(
				"frappe/claude-opus-5-5",
				[{"role": "system", "content": "sys"}, {"role": "user", "content": "Add pricing"}],
				self.TOOLS,
				llm.Effort(None).params("agent"),
			)
		[body] = api.bodies
		self.assert_opus_5_5_takes(body, "medium")
		self.assertEqual(body["model"], "claude-opus-5-5")

	def test_a_page_generation_after_a_status_line(self):
		history = [{"role": "user", "content": "Build it"}, {"role": "assistant", "content": "Applied."}]
		with CapturedAnthropic() as api:
			llm.complete("frappe/claude-opus-5-5", history, llm.TASK_PARAMS["complex"], stream=False)
		[body] = api.bodies
		self.assert_opus_5_5_takes(body, "high")

	def test_a_chat_title(self):
		with CapturedAnthropic() as api:
			title = llm.complete(
				"frappe/claude-opus-5-5",
				[{"role": "user", "content": "Name this chat"}],
				{"max_tokens": 24, "temperature": 0.3},
				stream=False,
			)
		[body] = api.bodies
		self.assert_opus_5_5_takes(body, "low")
		self.assertEqual(title, "Pricing Plans")


class TestRefusal(FrappeTestCase):
	"""A refusal (finish_reason content_filter from litellm) ends the turn with words, applying nothing of
	the round it cut off."""

	def setUp(self):
		self.tag = frappe.generate_hash(length=6)
		self.page = make_page("Home", f"refusal-{self.tag}", [heading("head1", "Welcome")])
		self.session_id = AISession.create({"page": self.page}).name

	def test_a_refused_round_applies_nothing_and_says_why(self):
		half_call = tool_call("edit_page", {"ops": '@head1 "Changed"'})
		refused = iter([chunk(content="Sure, ", tool_calls=[half_call], finish_reason=llm.REFUSED)])
		events = []
		runner = AgentRunner("change it", "m", "k", page_id=self.page, session_id=self.session_id)
		with (
			patch.object(llm, "complete_with_tools", return_value=refused),
			patch("frappe.publish_realtime", lambda event, message, **kw: events.append((event, message))),
			patch.object(AgentRunner, "maybe_name_session"),
		):
			runner.run()
		self.assertEqual(texts(self.page)["head1"], "Welcome")
		reply = AISession.get(self.session_id).get_messages()[-1]
		self.assertEqual(reply["content"], llm.REFUSAL_NOTE)
		self.assertEqual(runner.stop_reason, "refused")
		self.assertFalse([e for e, _ in events if "error" in e])

	def test_a_refused_page_generation_keeps_no_partial_page(self):
		from builder.ai.agent.artifact import generate_page_markup

		runner = AgentRunner("build it", "m", "k", page_id=self.page, session_id=self.session_id)
		partial = iter([chunk(content="section\n  h1 Pri", finish_reason=llm.REFUSED)])
		with (
			patch.object(llm, "complete", return_value=partial),
			patch("frappe.publish_realtime"),
			self.assertRaises(llm.Refused),
		):
			generate_page_markup(runner, {"brief": "A pricing page"})
		self.assertEqual(texts(self.page)["head1"], "Welcome")


def thought(text):
	"""A chunk of Claude's thinking summary, which comes before any of the answer."""
	delta = SimpleNamespace(content=None, tool_calls=None, reasoning_content=text)
	return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)], usage=None)


class TestPageGenerationThinking(FrappeTestCase):
	"""Claude plans a whole page before it writes a line of it, which can take a minute or more: its thinking
	streams into a thinking step meanwhile, so neither the chat nor the canvas sits silent."""

	def setUp(self):
		self.tag = frappe.generate_hash(length=6)
		self.page = make_page("Home", f"thinking-{self.tag}", [heading("head1", "Welcome")])
		self.session_id = AISession.create({"page": self.page}).name

	def generate(self, stream):
		from builder.ai.agent.artifact import generate_page_markup

		events = []
		runner = AgentRunner("build it", "m", "k", page_id=self.page, session_id=self.session_id)
		with (
			patch.object(llm, "complete", return_value=iter(stream)),
			patch("frappe.publish_realtime", lambda event, message, **kw: events.append((event, message))),
		):
			generate_page_markup(runner, {"brief": "A page for a bakery"})
		return runner, events

	def test_the_plan_streams_into_a_thinking_step_that_ends_when_the_page_starts(self):
		runner, events = self.generate(
			[
				thought("A warm hero, "),
				thought("then three breads."),
				chunk(content='section\n  h1 "Crumb"\n', finish_reason="stop"),
			]
		)
		[step] = [s for s in runner.steps if s["kind"] == "thinking"]
		self.assertEqual(step["text"], "A warm hero, then three breads.")
		self.assertEqual(step["status"], "done")
		streamed = "".join(m["chunk"] for _, m in events if m.get("kind") == "reasoning")
		self.assertEqual(streamed, step["text"])
		self.assertIn(step, runner.timeline())

	def test_a_model_that_shows_no_thinking_leaves_no_thinking_on_the_message(self):
		runner, _ = self.generate([chunk(content='section\n  h1 "Crumb"\n', finish_reason="stop")])
		self.assertFalse([s for s in runner.timeline() if s["kind"] == "thinking"])
		self.assertTrue(all(s["status"] == "done" for s in runner.steps if s["kind"] == "thinking"))


class TestAnthropicSiteKey(FrappeTestCase):
	"""`ai_keys: [{"provider": "anthropic", "api_key": ...}]`: Anthropic's own API as the Frappe provider."""

	def setUp(self):
		test_presets.TestSiteProvider.setUp(self)
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "")
		frappe.db.set_default(ADOPTED_DEFAULT_KEY, "")
		frappe.cache.delete_value(GatewayListing.cache_key("Frappe"))
		self.addCleanup(frappe.cache.delete_value, GatewayListing.cache_key("Frappe"))
		self.addCleanup(ModelRegistry.clear_cache)
		self.enterContext(patch("builder.ai.presets.preferred_model", return_value="claude-opus-5-5"))
		self.enterContext(patch("builder.ai.models.fetch_openrouter_catalog", return_value={}))

	def sync(self, conf=ANTHROPIC_SITE_KEY):
		with (
			site_config(conf),
			patch("builder.ai.models.requests.get", return_value=listing_response()) as get,
		):
			sync_site_provider()
		return frappe.get_doc("Builder AI Provider", "Frappe"), get

	def test_the_entry_shapes(self):
		self.assertEqual(
			SiteAIKey.from_entry(
				{"provider": "anthropic", "api_key": "k", "gateway_url": "https://elsewhere.test"}
			),
			SiteAIKey("anthropic", "k"),
		)
		self.assertEqual(
			SiteAIKey.from_entry({"gateway_url": "https://grove.test", "api_key": "k"}),
			SiteAIKey("gateway", "k", "https://grove.test"),
		)
		for broken in ({"provider": "anthropic"}, {"provider": "openai", "api_key": "k"}, {"api_key": "k"}):
			with self.subTest(broken=broken):
				self.assertIsNone(SiteAIKey.from_entry(broken))

	def test_it_lists_its_models_from_anthropic_with_its_own_headers(self):
		provider, get = self.sync()
		self.assertEqual(
			(provider.enabled, provider.litellm_provider, provider.api_base), (1, "anthropic", None)
		)
		self.assertEqual(get.call_args.args[0], f"{ANTHROPIC_API}/v1/models?limit=1000")
		self.assertEqual(
			get.call_args.kwargs["headers"], {"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"}
		)

	def test_it_offers_the_current_models_with_opus_5_5_the_default(self):
		self.sync()
		rows = frappe.get_all(
			"Builder AI Model",
			filters={"provider": "Frappe", "enabled": 1},
			fields=["model_id", "label", "supports_vision", "max_tokens"],
			order_by="frontier_rank asc",
		)
		self.assertEqual(
			[r.model_id for r in rows], ["claude-opus-5-5", "claude-fable-5-2", "claude-sonnet-5-5"]
		)
		opus = (rows[0].label, rows[0].supports_vision, rows[0].max_tokens)
		self.assertEqual(opus, ("Display name of claude-opus-5-5", 1, 1_000_000))
		self.assertEqual(
			frappe.db.get_single_value("Builder Settings", "default_ai_model"), "frappe/claude-opus-5-5"
		)

	def test_the_picker_puts_the_host_s_default_first_even_on_rows_listed_before(self):
		self.sync()
		with (
			site_config(ANTHROPIC_SITE_KEY),
			patch("builder.ai.models.requests.get", return_value=listing_response()),
			patch("builder.ai.presets.preferred_model", return_value="claude-sonnet-5-5"),
		):
			GatewayListing(frappe.get_doc("Builder AI Provider", "Frappe")).sync()
			first = ModelRegistry.available()[0]["models"][0]["name"]
		self.assertEqual(first, "frappe/claude-sonnet-5-5")

	def test_the_current_models(self):
		retiring = claude(
			"claude-opus-5-6", "opus", "2026-12-01T00:00:00Z", deprecated_at="2027-01-01T00:00:00Z"
		)
		blind = claude("claude-sonnet-5-6", "sonnet", "2026-12-01T00:00:00Z", image=False)
		ids = [m["id"] for m in current_claude_models([retiring, blind, *LISTED], keep="claude-opus-5-5")]
		self.assertEqual(ids, ["claude-opus-5-5", "claude-fable-5-2", "claude-sonnet-5-5"])
		# the host's default is offered even when the policy would leave it out
		ids = [m["id"] for m in current_claude_models(LISTED, keep="claude-haiku-5-5")]
		self.assertEqual(ids[0], "claude-haiku-5-5")

	def test_calls_go_to_anthropic_natively_whatever_the_row_says(self):
		self.sync()
		frappe.db.set_value(
			"Builder AI Provider",
			"Frappe",
			{"api_base": "https://evil.test/v1", "litellm_provider": "openai"},
		)
		ModelRegistry.clear_cache()
		with site_config(ANTHROPIC_SITE_KEY):
			self.assertEqual(
				llm.route("frappe/claude-opus-5-5", None),
				(OPUS, {"api_base": ANTHROPIC_API}, ANTHROPIC_KEY),
			)
			provider = frappe.get_doc("Builder AI Provider", "Frappe")
			self.assertTrue(GatewayListing(provider).request()[0].startswith(f"{ANTHROPIC_API}/"))

	def test_no_balance_is_asked_for_or_shown(self):
		from builder.ai.api import get_provider_credits, get_site_ai_credits

		provider, _ = self.sync()
		with (
			site_config(ANTHROPIC_SITE_KEY),
			patch("builder.ai.models.requests.get") as get,
			patch("builder.ai.site_key.allowance", return_value=None),
		):
			self.assertIsNone(provider.credits_url)
			self.assertIsNone(get_site_ai_credits())
			self.assertIsNone(get_provider_credits("Frappe"))
		get.assert_not_called()

	def test_only_the_key_is_kept_from_users(self):
		from builder.ai.site_key import redact

		with site_config(ANTHROPIC_SITE_KEY):
			self.assertEqual(
				redact(f"401 from api.anthropic.com for {ANTHROPIC_KEY}"),
				f"401 from api.anthropic.com for {REDACTED}",
			)

	def test_moving_from_a_gateway_to_anthropic_replaces_the_gateway_models(self):
		with (
			site_config(SITE_KEY),
			patch("builder.ai.models.fetch_listing", return_value=["openai/gpt-6.1-sol"]),
		):
			sync_site_provider()
		frappe.db.set_single_value("Builder Settings", "default_ai_model", "frappe/openai/gpt-6.1-sol")
		self.sync()
		models = frappe.get_all("Builder AI Model", filters={"provider": "Frappe"}, pluck="model_id")
		self.assertNotIn("openai/gpt-6.1-sol", models)
		self.assertIn("claude-opus-5-5", models)
		self.assertEqual(
			frappe.db.get_single_value("Builder Settings", "default_ai_model"), "frappe/claude-opus-5-5"
		)

	def test_a_default_of_the_site_s_own_stays(self):
		mine = frappe.get_doc(
			{"doctype": "Builder AI Provider", "provider_name": "Mine", "api_base": "https://mine.test/v1"}
		).insert(ignore_permissions=True)
		self.addCleanup(
			frappe.delete_doc, "Builder AI Provider", mine.name, force=True, ignore_permissions=True
		)
		own = frappe.get_doc(
			{"doctype": "Builder AI Model", "provider": mine.name, "model_id": "my-model", "enabled": 1}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Builder AI Model", own.name, force=True, ignore_permissions=True)
		frappe.db.set_single_value("Builder Settings", "default_ai_model", own.name)
		self.sync()
		self.assertEqual(frappe.db.get_single_value("Builder Settings", "default_ai_model"), own.name)


class TestAnthropicUsage(FrappeTestCase):
	"""What a call on the site key settles with, from the usage Anthropic reports through litellm."""

	def test_cache_reads_and_writes_are_told_apart(self):
		from litellm import AnthropicConfig

		reported = AnthropicConfig().calculate_usage(
			{
				"input_tokens": 100,
				"output_tokens": 40,
				"cache_read_input_tokens": 5000,
				"cache_creation_input_tokens": 3000,
				"cache_creation": {"ephemeral_5m_input_tokens": 1000, "ephemeral_1h_input_tokens": 2000},
			},
			None,
		)
		charge = Charge(MagicMock(), prompt_estimate=0)
		self.assertEqual(
			charge.used(reported),
			Usage(
				prompt_tokens=8100,
				completion_tokens=40,
				cached_tokens=5000,
				cache_write_tokens=3000,
				cache_write_1h_tokens=2000,
			),
		)
