from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from builder.ai import llm
from builder.ai.site_key import (
	IMAGE_TOKENS,
	REDACTED,
	REDACTED_GATEWAY,
	Charge,
	Usage,
	UsageLimitError,
	ensure_allowance_left,
	estimate_tokens,
	is_site_key,
	redact,
	scrub_exception,
)

KEY = "grove-key-0123456789"
GATEWAY = "https://grove.test"
MESSAGES = [{"role": "user", "content": "Make me a page"}]


class Meter:
	"""An allowance that records what it was asked."""

	def __init__(self, refuse: str | None = None):
		self.refuse = refuse
		self.holds: list[int] = []
		self.settled: list[Usage] = []

	def reserve(self, tokens: int):
		if self.refuse:
			raise UsageLimitError(self.refuse)
		self.holds.append(tokens)
		return SimpleNamespace(settle=self.settled.append)

	def check(self) -> None:
		if self.refuse:
			raise UsageLimitError(self.refuse)

	def status(self) -> dict:
		return {}


def usage(prompt=100, completion=20, cached=0):
	return SimpleNamespace(
		prompt_tokens=prompt,
		completion_tokens=completion,
		prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
	)


def chunk(text: str | None = None, final_usage=None):
	choices = (
		[] if text is None else [SimpleNamespace(delta=SimpleNamespace(content=text), finish_reason=None)]
	)
	return SimpleNamespace(choices=choices, usage=final_usage)


class SiteKeyTestCase(FrappeTestCase):
	def setUp(self):
		self.meter = Meter()
		for target, value in (
			("builder.ai.site_key.site_entry", {"gateway_url": GATEWAY, "api_key": KEY}),
			("builder.ai.llm.codex_route", None),
			(
				"builder.ai.llm.route",
				("openai/openai/gpt-6.1-sol", {"api_base": "https://grove.test/openai/v1"}, KEY),
			),
		):
			patcher = patch(target, return_value=value)
			patcher.start()
			self.addCleanup(patcher.stop)
		self.allowance = patch("builder.ai.site_key.allowance", side_effect=lambda: self.meter)
		self.allowance.start()
		self.addCleanup(self.allowance.stop)


class TestSiteKey(SiteKeyTestCase):
	def test_the_site_key_is_told_apart_from_any_other(self):
		self.assertTrue(is_site_key(KEY))
		self.assertFalse(is_site_key("my-own-key"))
		self.assertFalse(is_site_key(None))

	def test_the_key_is_taken_out_of_text_and_exceptions(self):
		self.assertEqual(redact(f"Bad key Bearer {KEY}!"), f"Bad key Bearer {REDACTED}!")
		cause = RuntimeError(f"401 for {KEY}")
		error = ValueError(f"gateway said: {KEY}")
		error.__cause__ = cause
		error.message = f"also {KEY}"
		scrub_exception(error)
		self.assertNotIn(KEY, str(error) + str(cause) + error.message)

	def test_the_gateway_address_is_taken_out_too(self):
		text = redact(
			"POST https://grove.test/openai/v1 failed: HTTPSConnectionPool(host='grove.test', port=443)"
		)
		self.assertNotIn("grove.test", text)
		self.assertIn(f"POST {REDACTED_GATEWAY}/openai/v1", text)
		# as requests raises it: urllib3's error, naming the host, inside its args
		inner = RuntimeError("HTTPSConnectionPool(host='grove.test', port=443): Max retries exceeded")
		inner.__context__ = OSError("HTTPSConnection(host='grove.test', port=443): refused")
		error = ConnectionError(inner)
		scrub_exception(error)
		self.assertNotIn("grove.test", str(error) + str(inner.__context__))

	def test_a_spent_allowance_is_known_before_a_turn_is_queued(self):
		self.meter = Meter(refuse="spent")
		with self.assertRaises(UsageLimitError):
			ensure_allowance_left(KEY)
		ensure_allowance_left("my-own-key")

	def test_an_image_counts_as_an_image_not_as_its_data(self):
		image = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + "A" * 300_000}}
		self.assertLess(estimate_tokens([{"role": "user", "content": [image]}]), IMAGE_TOKENS + 100)


class TestMeteredCalls(SiteKeyTestCase):
	def test_a_call_holds_its_most_and_settles_what_the_model_reported(self):
		response = MagicMock(
			choices=[MagicMock(message=MagicMock(content="hi"))], usage=usage(900, 30, cached=600)
		)
		with patch("litellm.completion", return_value=response):
			llm.complete("frappe/openai/gpt-6.1-sol", list(MESSAGES), {"max_tokens": 1000}, stream=False)
		self.assertEqual(len(self.meter.holds), 1)
		self.assertGreater(self.meter.holds[0], 1000)
		self.assertEqual(self.meter.settled, [Usage(900, 30, 600)])

	def test_a_whole_response_without_usage_costs_an_estimate_not_nothing(self):
		from litellm.types.utils import Usage as LitellmUsage

		answer = "z" * 300
		for reported in (None, LitellmUsage()):  # litellm can hand back an empty usage
			self.meter = Meter()
			response = SimpleNamespace(
				choices=[SimpleNamespace(message=SimpleNamespace(content=answer, tool_calls=None))],
				usage=reported,
			)
			with self.subTest(reported=reported), patch("litellm.completion", return_value=response):
				llm.complete("frappe/openai/gpt-6.1-sol", list(MESSAGES), {"max_tokens": 1000}, stream=False)
				[settled] = self.meter.settled
				self.assertFalse(settled.measured)
				self.assertEqual(settled.prompt_tokens, self.meter.holds[0] - 1000)  # the prompt it held
				self.assertEqual(settled.completion_tokens, 100)

	def test_a_stream_settles_once_it_ends(self):
		chunks = [chunk("Hel"), chunk("lo"), chunk(None, usage(50, 2))]
		with patch("litellm.completion", return_value=iter(chunks)):
			stream = llm.complete_with_tools("frappe/openai/gpt-6.1-sol", list(MESSAGES), [], {}, stream=True)
			self.assertEqual(self.meter.settled, [])
			self.assertEqual(len(list(stream)), 3)
		self.assertEqual(self.meter.settled, [Usage(50, 2, 0)])

	def test_a_closed_stream_closes_the_provider_stream_and_settles_an_estimate(self):
		provider_stream = MagicMock()
		provider_stream.__iter__.return_value = iter([chunk("x" * 30), chunk("y" * 30)])
		with patch("litellm.completion", return_value=provider_stream):
			stream = llm.complete("frappe/openai/gpt-6.1-sol", list(MESSAGES), {}, stream=True)
			next(stream)
			stream.close()
		provider_stream.close.assert_called_once()
		[settled] = self.meter.settled
		self.assertFalse(settled.measured)
		self.assertEqual(settled.completion_tokens, 10)

	def test_a_call_that_fails_costs_no_tokens_and_loses_the_key_from_its_error(self):
		with (
			patch("litellm.completion", side_effect=RuntimeError(f"echo Bearer {KEY}")),
			self.assertRaises(RuntimeError) as raised,
		):
			llm.complete("frappe/openai/gpt-6.1-sol", list(MESSAGES), {}, stream=False)
		self.assertNotIn(KEY, str(raised.exception))
		self.assertEqual(self.meter.settled, [Usage(0, 0)])

	def test_a_spent_allowance_stops_the_call_before_it_is_made(self):
		self.meter = Meter(refuse="This site has used today's AI allowance.")
		with patch("litellm.completion") as completion, self.assertRaises(UsageLimitError) as raised:
			llm.complete_with_tools("frappe/openai/gpt-6.1-sol", list(MESSAGES), [], {}, stream=True)
		completion.assert_not_called()
		self.assertEqual(llm.user_facing_error(raised.exception), "This site has used today's AI allowance.")

	def test_a_key_of_the_site_s_own_is_never_metered(self):
		response = MagicMock(choices=[MagicMock(message=MagicMock(content="hi"))], usage=usage())
		with (
			patch("builder.ai.llm.route", return_value=("openai/gpt-x", {}, "my-own-key")),
			patch("litellm.completion", return_value=response),
		):
			llm.complete("openai/gpt-x", list(MESSAGES), {}, stream=False)
		self.assertEqual((self.meter.holds, self.meter.settled), ([], []))

	def test_a_host_without_an_allowance_meters_nothing(self):
		self.allowance.stop()
		with patch("builder.ai.site_key.allowance", return_value=None):
			self.assertIsNone(Charge.open(KEY, MESSAGES, {}))
		self.allowance.start()
