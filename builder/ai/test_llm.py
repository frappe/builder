from frappe.tests.utils import FrappeTestCase

from builder.ai.llm import (
	is_retryable,
	loads_tolerant,
	patch_messages_for_provider,
	patch_params_for_provider,
	provider_kwargs,
	provider_overrides,
)

CLAUDE = "openrouter/anthropic/claude-sonnet-5"
GPT = "openrouter/openai/gpt-5.6-luna"


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
