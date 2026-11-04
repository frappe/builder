from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from builder.ai import openai_responses
from builder.ai.llm import selected_params
from builder.ai.models import ModelRegistry, model_controls
from builder.ai.workflow import ModelRequest

OPENAI = {
	"name": "openai/gpt-6.1-sol",
	"provider": "OpenAI",
	"route_prefix": "openai",
	"litellm_provider": "openai",
	"api_base": None,
}


class TestOpenAIResponses(TestCase):
	def test_controls_follow_the_model_and_transport(self):
		direct = model_controls(OPENAI)
		self.assertIn("max", direct["reasoning_efforts"])
		self.assertTrue(direct["fast_supported"])
		self.assertFalse(model_controls({**OPENAI, "api_base": "https://proxy.test"})["fast_supported"])
		self.assertFalse(model_controls({**OPENAI, "litellm_provider": "codex"})["fast_supported"])

	def test_only_direct_openai_gpt6_uses_responses(self):
		with patch.object(ModelRegistry, "find", return_value=OPENAI):
			self.assertEqual(openai_responses.route(OPENAI["name"]), "gpt-6.1-sol")
		with patch.object(ModelRegistry, "find", return_value={**OPENAI, "api_base": "https://proxy.test"}):
			self.assertIsNone(openai_responses.route(OPENAI["name"]))

	def test_agent_request_sends_reasoning_fast_and_function_tools(self):
		messages = [
			{"role": "system", "content": "Build a page"},
			{"role": "assistant", "content": "Thinking"},
			{"role": "user", "content": "Use a hero"},
		]
		tools = [{"type": "function", "function": {"name": "update_block", "parameters": {"type": "object"}}}]
		request = ModelRequest(
			OPENAI["name"], messages, selected_params("agent", "max", True), api_key="test-key", tools=tools
		)
		with patch.object(ModelRegistry, "find", return_value=OPENAI):
			request.prepare(asynchronous=True)
		payload = request.prepared["payload"]
		self.assertEqual(request.prepared["transport"], "openai_responses")
		self.assertEqual(payload["reasoning"]["effort"], "max")
		self.assertEqual(payload["service_tier"], "fast")
		self.assertEqual(payload["max_output_tokens"], 16000)
		self.assertEqual(payload["tools"][0]["name"], "update_block")
		self.assertFalse(payload["tools"][0]["strict"])
		self.assertEqual(
			next(item for item in payload["input"] if item.get("role") == "assistant"),
			{"role": "assistant", "content": "Thinking"},
		)
		self.assertEqual(request.prepared["headers"]["Authorization"], "Bearer test-key")

	def test_stream_reassembles_text_and_tool_calls(self):
		from builder.ai import codex

		events = [
			{"type": "response.output_text.delta", "delta": "Ready"},
			{
				"type": "response.output_item.added",
				"item": {"type": "function_call", "id": "item", "call_id": "call", "name": "update_block"},
			},
			{"type": "response.function_call_arguments.delta", "item_id": "item", "delta": '{"id":"hero"}'},
			{"type": "response.completed", "response": {"usage": {"input_tokens": 10, "output_tokens": 4}}},
		]
		assembler = codex.ChunkAssembler()
		response = openai_responses.collect_response(
			chunk for event in events for chunk in assembler.feed(event)
		)
		self.assertEqual(response.choices[0].message.content, "Ready")
		self.assertEqual(response.choices[0].message.tool_calls[0].function.arguments, '{"id":"hero"}')
		self.assertEqual(response.usage.total_tokens, 14)

	def test_http_failures_keep_actionable_error_types(self):
		for status, expected in (
			(401, "AuthenticationError"),
			(403, "PermissionDeniedError"),
			(404, "NotFoundError"),
			(429, "RateLimitError"),
			(500, "InternalServerError"),
		):
			with self.subTest(status=status):
				error = openai_responses.http_error(SimpleNamespace(status_code=status, text="failed"))
				self.assertEqual(type(error).__name__, expected)
				self.assertEqual(error.status_code, status)
