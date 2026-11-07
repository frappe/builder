from typing import ClassVar
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.llm import (
	GENERIC_FAILURE,
	NO_KEY,
	TASK_PARAMS,
	complete_with_tools,
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

	def test_a_payment_failure_says_so(self):
		class APIError(Exception):
			status_code = 402

		self.assertIn("out of credit", user_facing_error(APIError("check your payment status")))

	def test_an_unavailable_model_points_at_the_picker(self):
		class ServiceUnavailableError(Exception):
			pass

		self.assertIn("/model", user_facing_error(ServiceUnavailableError("model unavailable")))

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

	def test_thinking_claude_takes_temperature_one_only_from_anthropic_directly(self):
		thinking = {"temperature": 0.7, "reasoning_effort": "high"}
		self.assertEqual(patch_params_for_provider("anthropic/claude-sonnet-5", thinking)["temperature"], 1)
		self.assertEqual(
			patch_params_for_provider("openrouter/anthropic/claude-sonnet-5", thinking)["temperature"], 0.7
		)

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
	def test_only_openrouter_borrows_the_shared_key(self):
		proxied = {**OPENROUTER_MODEL, "api_base": "https://proxy.example.com/v1"}
		for info, expected in ((OPENROUTER_MODEL, SHARED_KEY), (GATEWAY_MODEL, NO_KEY), (proxied, NO_KEY)):
			with (
				self.subTest(model=info["name"], api_base=info["api_base"]),
				patch.object(ModelRegistry, "find", return_value=info),
				patch("builder.ai.llm.provider_api_key", return_value=None),
				patch("builder.ai.llm.settings_api_key", return_value=SHARED_KEY),
			):
				self.assertEqual(route(info["name"], SHARED_KEY)[2], expected)
				self.assertEqual(resolve_api_key(info["name"]), expected)


class TestGatewayToolCalls(FrappeTestCase):
	model = "openai/openai/gpt-6-luna"
	tools: ClassVar[list] = [
		{"type": "function", "function": {"name": "inspect_page", "parameters": {"type": "object"}}}
	]
	base: ClassVar[dict] = {"api_base": "https://gateway.example.com/openai/v1"}

	def missing_responses(self, message="openai/gpt-6-luna does not serve /v1/responses"):
		from litellm import NotFoundError

		return NotFoundError(message=message, model=self.model, llm_provider="openai")

	def call(self, completion, *, model=None, overrides=None, params=None, stream=False):
		with (
			patch("builder.ai.llm.codex_route", return_value=None),
			patch(
				"builder.ai.llm.route",
				return_value=(model or self.model, self.base if overrides is None else overrides, "test-key"),
			),
			patch("litellm.completion", side_effect=completion) as complete,
		):
			result = complete_with_tools(
				"frappe/openai/gpt-6-luna",
				[{"role": "user", "content": "Inspect the page"}],
				self.tools,
				TASK_PARAMS["agent"] if params is None else params,
				stream=stream,
			)
			return result, complete.call_args_list

	def test_retries_an_unsupported_responses_route_without_reasoning(self):
		for stream in (False, True):
			with self.subTest(stream=stream):
				response = object()
				result, calls = self.call([self.missing_responses(), response], stream=stream)
				self.assertIs(result, response)
				self.assertEqual(len(calls), 2)
				first, retry = (call.kwargs for call in calls)
				self.assertEqual(first["reasoning_effort"], "medium")
				self.assertEqual(retry, {k: v for k, v in first.items() if k != "reasoning_effort"})
				self.assertEqual(retry["tools"], self.tools)
				self.assertEqual(retry["stream"], stream)
				self.assertEqual(TASK_PARAMS["agent"]["reasoning_effort"], "medium")

	def test_keeps_reasoning_when_the_gateway_serves_the_request(self):
		response = object()
		result, calls = self.call([response])
		self.assertIs(result, response)
		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0].kwargs["reasoning_effort"], "medium")

	def test_does_not_retry_other_models_or_provider_errors(self):
		from litellm import AuthenticationError

		cases = [
			(self.missing_responses(), {"overrides": {}}),
			(self.missing_responses(), {"model": "openrouter/openai/gpt-6-luna"}),
			(self.missing_responses(), {"params": {"max_tokens": 1000}}),
			(self.missing_responses("The selected model does not exist"), {}),
			(AuthenticationError(message="Invalid key", model=self.model, llm_provider="openai"), {}),
		]
		for error, options in cases:
			with self.subTest(error=str(error), options=options), self.assertRaises(type(error)) as raised:
				self.call([error], **options)
			self.assertIs(raised.exception, error)

	def test_a_failed_fallback_is_not_retried_again(self):
		error = self.missing_responses()
		with self.assertRaises(type(error)) as raised:
			self.call([self.missing_responses(), error])
		self.assertIs(raised.exception, error)
