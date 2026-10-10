from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.api import import_provider_models
from builder.ai.llm import (
	GENERIC_FAILURE,
	is_retryable,
	loads_tolerant,
	patch_messages_for_provider,
	patch_params_for_provider,
	provider_kwargs,
	provider_overrides,
	resolve_api_key,
	route,
	user_facing_error,
)
from builder.ai.models import ModelRegistry

CLAUDE = "openrouter/anthropic/claude-sonnet-5"
GPT = "openrouter/openai/gpt-5.6-luna"
SHARED_KEY = "sk-or-shared"
OPENROUTER_MODEL = {
	"name": CLAUDE,
	"provider": "OpenRouter",
	"route_prefix": "openrouter",
	"litellm_provider": "openrouter",
	"api_base": None,
}
GATEWAY_MODEL = {
	"name": "gateway/llama-4",
	"provider": "Gateway",
	"route_prefix": "gateway",
	"litellm_provider": "openai",
	"api_base": "https://gateway.example.com/v1",
}


class RateLimitError(Exception):
	pass


class TestRetryable(FrappeTestCase):
	def test_a_rate_limit_is_transient(self):
		self.assertTrue(is_retryable(RateLimitError()))

	def test_a_subclass_is_transient_too(self):
		class Wrapped(RateLimitError):
			pass

		self.assertTrue(is_retryable(Wrapped()))

	def test_a_value_error_is_not(self):
		self.assertFalse(is_retryable(ValueError("bad args")))


class AuthenticationError(Exception):
	pass


class TestUserFacingError(FrappeTestCase):
	def test_a_rejected_key_says_where_to_fix_it(self):
		message = user_facing_error(AuthenticationError("Missing Authentication header sk-or-secret"))

		self.assertIn("API key", message)
		self.assertNotIn("sk-or-secret", message)

	def test_a_subclass_maps_like_its_parent(self):
		class ProviderAuthError(AuthenticationError):
			pass

		self.assertIn("API key", user_facing_error(ProviderAuthError()))

	def test_a_chatgpt_sign_in_problem_asks_to_sign_in_again(self):
		from builder.ai.codex import CodexCredentialError, CodexError

		self.assertIn("Sign in with ChatGPT", user_facing_error(CodexCredentialError("expired")))
		self.assertEqual(user_facing_error(CodexError("stream failed")), GENERIC_FAILURE)

	def test_anything_else_stays_generic(self):
		self.assertEqual(user_facing_error(ValueError("internal detail")), GENERIC_FAILURE)


class TestLoadsTolerant(FrappeTestCase):
	def test_parses_clean_json(self):
		self.assertEqual(loads_tolerant('{"a": 1}'), ({"a": 1}, False))

	def test_repairs_a_trailing_comma(self):
		parsed, repaired = loads_tolerant('{"a": 1,}')

		self.assertEqual(parsed, {"a": 1})
		self.assertTrue(repaired)

	def test_repairs_single_quotes(self):
		parsed, repaired = loads_tolerant("{'a': 1}")

		self.assertEqual(parsed, {"a": 1})
		self.assertTrue(repaired)

	def test_repairs_a_truncated_object(self):
		parsed, _ = loads_tolerant('{"a": "b"')

		self.assertEqual(parsed, {"a": "b"})

	def test_returns_nothing_for_empty_input(self):
		self.assertEqual(loads_tolerant("   "), (None, False))


class TestCacheMarkers(FrappeTestCase):
	def test_moves_the_marker_into_the_last_content_block_for_claude(self):
		messages = [{"role": "user", "content": "hi", "cache_control": {"type": "ephemeral"}}]
		patch_messages_for_provider(CLAUDE, messages)

		self.assertNotIn("cache_control", messages[0])
		self.assertEqual(messages[0]["content"][-1]["cache_control"], {"type": "ephemeral"})

	def test_marks_the_last_part_of_a_multipart_message(self):
		messages = [
			{
				"role": "user",
				"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}],
				"cache_control": {"type": "ephemeral"},
			}
		]
		patch_messages_for_provider(CLAUDE, messages)

		self.assertNotIn("cache_control", messages[0]["content"][0])
		self.assertIn("cache_control", messages[0]["content"][1])

	def test_strips_the_marker_for_other_providers(self):
		messages = [{"role": "user", "content": "hi", "cache_control": {"type": "ephemeral"}}]
		patch_messages_for_provider(GPT, messages)

		self.assertEqual(messages, [{"role": "user", "content": "hi"}])


class TestProviderTuning(FrappeTestCase):
	def test_pins_claude_to_anthropic(self):
		order = provider_kwargs(CLAUDE)["extra_body"]["provider"]

		self.assertEqual(order["order"], ["anthropic"])
		self.assertFalse(order["allow_fallbacks"])

	def test_leaves_other_models_unpinned(self):
		self.assertEqual(provider_kwargs(GPT), {})

	def test_coerces_kimi_to_temperature_one(self):
		self.assertEqual(patch_params_for_provider("kimi-k2", {"temperature": 0.7})["temperature"], 1)

	def test_leaves_other_temperatures_alone(self):
		self.assertEqual(patch_params_for_provider(GPT, {"temperature": 0.7})["temperature"], 0.7)

	def test_passes_through_a_configured_api_base(self):
		self.assertEqual(
			provider_overrides({"api_base": "https://gw.example.com"}),
			{"api_base": "https://gw.example.com"},
		)

	def test_omits_an_api_base_that_is_not_set(self):
		self.assertEqual(provider_overrides({}), {})


class TestSharedKey(FrappeTestCase):
	def routed_key(self, info: dict) -> str | None:
		with (
			patch.object(ModelRegistry, "find", return_value=info),
			patch("builder.ai.llm.provider_api_key", return_value=None),
		):
			return route(info["name"], SHARED_KEY)[2]

	def test_an_openrouter_model_without_its_own_key_borrows_the_shared_one(self):
		self.assertEqual(self.routed_key(OPENROUTER_MODEL), SHARED_KEY)

	def test_a_custom_gateway_never_gets_the_shared_key(self):
		self.assertNotEqual(self.routed_key(GATEWAY_MODEL), SHARED_KEY)

	def test_openrouter_behind_a_custom_api_base_never_gets_the_shared_key(self):
		self.assertNotEqual(
			self.routed_key({**OPENROUTER_MODEL, "api_base": "https://proxy.example.com"}), SHARED_KEY
		)

	def resolved_key(self, info: dict) -> str:
		with (
			patch.object(ModelRegistry, "find", return_value=info),
			patch("builder.ai.llm.provider_api_key", return_value=None),
			patch("builder.ai.llm.settings_api_key", return_value=SHARED_KEY),
		):
			return resolve_api_key(info["name"])

	def test_resolves_the_shared_key_only_for_openrouter(self):
		self.assertEqual(self.resolved_key(OPENROUTER_MODEL), SHARED_KEY)
		self.assertNotEqual(self.resolved_key(GATEWAY_MODEL), SHARED_KEY)

	def test_importing_a_gateways_models_never_sends_the_shared_key(self):
		provider = frappe.get_doc(
			{
				"doctype": "Builder AI Provider",
				"provider_name": "Bob Keyless Gateway",
				"api_base": GATEWAY_MODEL["api_base"],
			}
		).insert()

		with (
			patch("builder.ai.llm.settings_api_key", return_value=SHARED_KEY),
			patch("requests.get") as get,
		):
			get.return_value.json.return_value = {"data": []}
			import_provider_models(provider.name)

		self.assertNotIn("Authorization", get.call_args.kwargs["headers"])
