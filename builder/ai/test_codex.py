"""Unit tests for the Codex adapter (builder/ai/codex.py).

Pure-function tests (no DB, no network): they pin the chat->Responses transcript
translation and the SSE->chat-chunk assembly the agent loop depends on.
"""

import base64
import json
import unittest

from builder.ai import codex


def fake_jwt(claims: dict) -> str:
	payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
	return f"header.{payload}.signature"


class TestParseCredential(unittest.TestCase):
	def test_normalizes_cli_auth_json(self):
		access = fake_jwt({"exp": 1000, "https://api.openai.com/auth": {"chatgpt_account_id": "acct_1"}})
		raw = json.dumps(
			{
				"auth_mode": "chatgpt",
				"tokens": {"access_token": access, "refresh_token": "rt_1", "account_id": "acct_1"},
			}
		)
		cred = codex.parse_credential(raw)
		self.assertEqual(cred["refresh"], "rt_1")
		self.assertEqual(cred["account_id"], "acct_1")
		self.assertEqual(cred["expires"], 1000 * 1000)

	def test_account_id_falls_back_to_jwt_claim(self):
		access = fake_jwt({"exp": 1, "https://api.openai.com/auth": {"chatgpt_account_id": "acct_jwt"}})
		raw = json.dumps({"tokens": {"access_token": access, "refresh_token": "rt"}})
		self.assertEqual(codex.parse_credential(raw)["account_id"], "acct_jwt")

	def test_own_shape_passes_through(self):
		raw = json.dumps({"access": "a", "refresh": "r", "expires": 5, "account_id": "acct"})
		self.assertEqual(codex.parse_credential(raw)["refresh"], "r")

	def test_rejects_garbage_and_missing_refresh(self):
		with self.assertRaises(codex.CodexError):
			codex.parse_credential("not json")
		with self.assertRaises(codex.CodexError):
			codex.parse_credential(json.dumps({"tokens": {"access_token": "x"}}))


class TestResponsesInput(unittest.TestCase):
	def test_full_transcript(self):
		messages = [
			{"role": "system", "content": "Be helpful", "cache_control": {"type": "ephemeral"}},
			{"role": "user", "content": "Build a page"},
			{
				"role": "assistant",
				"content": "On it",
				"tool_calls": [
					{"id": "call_1", "type": "function", "function": {"name": "plan", "arguments": '{"a":1}'}}
				],
			},
			{"role": "tool", "tool_call_id": "call_1", "content": "done"},
		]
		instructions, items = codex.responses_input(messages)
		self.assertEqual(instructions, "Be helpful")
		self.assertEqual(
			items[0], {"role": "user", "content": [{"type": "input_text", "text": "Build a page"}]}
		)
		self.assertEqual(items[1]["type"], "message")
		self.assertEqual(items[1]["content"][0]["text"], "On it")
		self.assertEqual(
			items[2],
			{"type": "function_call", "call_id": "call_1", "name": "plan", "arguments": '{"a":1}'},
		)
		self.assertNotIn("id", items[2])  # an item id would demand the reasoning chain
		self.assertEqual(items[3], {"type": "function_call_output", "call_id": "call_1", "output": "done"})

	def test_multimodal_user_content(self):
		messages = [
			{
				"role": "user",
				"content": [
					{"type": "text", "text": "match this"},
					{"type": "image_url", "image_url": {"url": "data:image/png;base64,xyz"}},
				],
			}
		]
		_, items = codex.responses_input(messages)
		self.assertEqual(
			items[0]["content"],
			[
				{"type": "input_text", "text": "match this"},
				{"type": "input_image", "image_url": "data:image/png;base64,xyz"},
			],
		)

	def test_mid_transcript_system_degrades_to_user(self):
		_, items = codex.responses_input(
			[{"role": "user", "content": "hi"}, {"role": "system", "content": "note"}]
		)
		self.assertEqual(items[1]["role"], "user")

	def test_tool_schema_translation(self):
		tools = [
			{
				"type": "function",
				"function": {"name": "plan", "description": "d", "parameters": {"type": "object"}},
			}
		]
		out = codex.responses_tools(tools)
		self.assertEqual(
			out,
			[
				{
					"type": "function",
					"name": "plan",
					"description": "d",
					"parameters": {"type": "object"},
					"strict": None,
				}
			],
		)


class TestChunkAssembler(unittest.TestCase):
	def collect(self, events):
		assembler = codex.ChunkAssembler()
		chunks = []
		for event in events:
			chunks.extend(assembler.feed(event))
		return assembler, chunks

	def accumulate_calls(self, chunks):
		"""Mirror stream_tool_round's accumulation by index."""
		acc = {}
		for c in chunks:
			for tc in c.choices[0].delta.tool_calls or []:
				entry = acc.setdefault(tc.index, {"id": None, "name": None, "args": ""})
				if tc.id:
					entry["id"] = tc.id
				if tc.function.name:
					entry["name"] = tc.function.name
				if tc.function.arguments:
					entry["args"] += tc.function.arguments
		return acc

	def test_tool_call_stream_with_done_topup(self):
		events = [
			{
				"type": "response.output_item.added",
				"item": {"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": "plan"},
			},
			{"type": "response.function_call_arguments.delta", "item_id": "fc_1", "delta": '{"a"'},
			{"type": "response.function_call_arguments.delta", "item_id": "fc_1", "delta": ":1"},
			{
				"type": "response.output_item.done",
				"item": {
					"type": "function_call",
					"id": "fc_1",
					"call_id": "call_1",
					"name": "plan",
					"arguments": '{"a":1}',
				},
			},
			{
				"type": "response.completed",
				"response": {
					"usage": {
						"input_tokens": 10,
						"output_tokens": 4,
						"input_tokens_details": {"cached_tokens": 8},
					}
				},
			},
		]
		assembler, chunks = self.collect(events)
		acc = self.accumulate_calls(chunks)
		self.assertEqual(acc, {0: {"id": "call_1", "name": "plan", "args": '{"a":1}'}})
		final = chunks[-1]
		self.assertEqual(final.choices[0].finish_reason, "tool_calls")
		self.assertEqual(final.usage.prompt_tokens, 10)
		self.assertEqual(final.usage.total_tokens, 14)
		self.assertEqual(final.usage.prompt_tokens_details.cached_tokens, 8)
		self.assertTrue(assembler.finished)

	def test_done_without_added_still_emits_the_call(self):
		events = [
			{
				"type": "response.output_item.done",
				"item": {"type": "function_call", "call_id": "call_9", "name": "edit", "arguments": "{}"},
			},
			{"type": "response.completed", "response": {}},
		]
		_, chunks = self.collect(events)
		self.assertEqual(self.accumulate_calls(chunks), {0: {"id": "call_9", "name": "edit", "args": "{}"}})

	def test_text_and_reasoning_stream(self):
		events = [
			{
				"type": "response.reasoning_summary_text.delta",
				"item_id": "rs_1",
				"summary_index": 0,
				"delta": "thinking",
			},
			{
				"type": "response.reasoning_summary_text.delta",
				"item_id": "rs_1",
				"summary_index": 1,
				"delta": "more",
			},
			{"type": "response.output_text.delta", "item_id": "msg_1", "delta": "Hello"},
			{
				"type": "response.output_item.done",
				"item": {
					"type": "message",
					"id": "msg_1",
					"content": [{"type": "output_text", "text": "Hello"}],
				},
			},
			{"type": "response.completed", "response": {}},
		]
		_, chunks = self.collect(events)
		reasoning = "".join(c.choices[0].delta.reasoning_content or "" for c in chunks)
		content = "".join(c.choices[0].delta.content or "" for c in chunks)
		self.assertEqual(reasoning, "thinking\n\nmore")
		self.assertEqual(content, "Hello")  # the done event must not double the streamed text
		self.assertEqual(chunks[-1].choices[0].finish_reason, "stop")

	def test_unstreamed_message_text_arrives_at_done(self):
		events = [
			{
				"type": "response.output_item.done",
				"item": {
					"type": "message",
					"id": "msg_1",
					"content": [{"type": "output_text", "text": "All set"}],
				},
			},
			{"type": "response.completed", "response": {}},
		]
		_, chunks = self.collect(events)
		self.assertEqual("".join(c.choices[0].delta.content or "" for c in chunks), "All set")

	def test_incomplete_maps_to_length(self):
		_, chunks = self.collect([{"type": "response.incomplete", "response": {}}])
		self.assertEqual(chunks[-1].choices[0].finish_reason, "length")

	def test_failure_event_raises(self):
		assembler = codex.ChunkAssembler()
		with self.assertRaises(codex.CodexError):
			assembler.feed({"type": "response.failed", "response": {"error": {"message": "boom"}}})


class FakeResponse:
	def __init__(self, lines):
		self.lines = lines

	def iter_lines(self):
		return iter(self.lines)


class TestIterSse(unittest.TestCase):
	def test_decodes_byte_lines_and_stops_at_done(self):
		# requests yields BYTES here: text/event-stream has no charset
		resp = FakeResponse(
			[
				b'data: {"type": "response.output_text.delta",',
				b'data: "delta": "hi"}',
				b"",
				b"data: [DONE]",
				b'data: {"type": "never-reached"}',
			]
		)
		events = list(codex.iter_sse(resp))
		self.assertEqual(events, [{"type": "response.output_text.delta", "delta": "hi"}])


class TestPayload(unittest.TestCase):
	def test_no_tuning_params_leak_into_the_payload(self):
		# the backend 400s on temperature and max_output_tokens alike
		payload = codex.build_payload("gpt-5.6-terra", [{"role": "user", "content": "hi"}], tools=None)
		self.assertNotIn("max_output_tokens", payload)
		self.assertNotIn("temperature", payload)
		self.assertFalse(payload["store"])
		self.assertEqual(payload["reasoning"], {"summary": "auto"})


if __name__ == "__main__":
	unittest.main()
