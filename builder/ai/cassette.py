"""Record/replay cassettes for LLM calls — test the whole agent for free.

One paid run in record mode captures every LLM response (streams included) to
a jsonl episode under the site's private files. Replay mode serves them back
in sequence without touching the provider, so full agent turns — tool routing,
canvas events, persistence, cancellation — run deterministically at zero cost.

Arming is a Redis flag (no restart needed, workers see it immediately):

    from builder.ai import cassette
    cassette.arm("record", "rename-turn")   # then drive one real turn
    cassette.arm("replay", "rename-turn")   # then drive the same turn, free
    cassette.disarm()

Calls are matched by SEQUENCE, not by exact prompt bytes — page ids and
timestamps differ between runs, and that must not break replay. A prompt-hash
mismatch is logged as drift (the test changed meaningfully) but still served.
Recording is meant for one run at a time: concurrent workers appending to one
episode would interleave.
"""

import hashlib
import json
import os

import frappe

logger = frappe.logger("builder.ai.cassette")

CONFIG_KEY = "ai_llm_cassette"
EPISODE_TTL = 3600


def config() -> dict | None:
	raw = frappe.cache().get_value(CONFIG_KEY)
	return raw if isinstance(raw, dict) and raw.get("mode") in ("record", "replay") else None


def arm(mode: str, episode: str) -> None:
	if mode not in ("record", "replay"):
		raise ValueError("mode must be 'record' or 'replay'")
	if mode == "record" and os.path.exists(episode_path(episode)):
		os.remove(episode_path(episode))
	frappe.cache().delete_value(seq_key(episode))
	frappe.cache().set_value(CONFIG_KEY, {"mode": mode, "episode": episode}, expires_in_sec=EPISODE_TTL)


def disarm() -> None:
	cfg = config()
	if cfg:
		frappe.cache().delete_value(seq_key(cfg["episode"]))
	frappe.cache().delete_value(CONFIG_KEY)


def episode_path(episode: str) -> str:
	directory = frappe.get_site_path("private", "files", "ai_cassettes")
	os.makedirs(directory, exist_ok=True)
	safe = "".join(c for c in episode if c.isalnum() or c in "-_")
	return os.path.join(directory, f"{safe}.jsonl")


def seq_key(episode: str) -> str:
	return f"ai_llm_cassette_seq:{episode}"


def next_seq(episode: str) -> int:
	cache = frappe.cache()
	return int(cache.incr(cache.make_key(seq_key(episode))))


def prompt_hash(model: str, messages: list) -> str:
	payload = json.dumps({"model": model, "messages": messages}, sort_keys=True, default=str)
	return hashlib.sha256(payload.encode()).hexdigest()[:12]


def append_record(episode: str, record: dict) -> None:
	with open(episode_path(episode), "a") as f:
		f.write(json.dumps(record, default=str) + "\n")


def load_record(episode: str, seq: int) -> dict:
	path = episode_path(episode)
	if not os.path.exists(path):
		raise FileNotFoundError(f"cassette episode not recorded: {path}")
	with open(path) as f:
		for line in f:
			record = json.loads(line)
			if record.get("seq") == seq:
				return record
	raise LookupError(f"cassette '{episode}' exhausted: no call #{seq} (recorded run made fewer LLM calls)")


class Replayed:
	"""Recursive attribute view over a recorded dict — quacks like a litellm
	response/chunk for every attribute the agent loop reads (choices, delta,
	tool_calls, usage, …)."""

	def __init__(self, data: dict):
		for key, value in data.items():
			setattr(self, key, self.wrap(value))

	@classmethod
	def wrap(cls, value):
		if isinstance(value, dict):
			return cls(value)
		if isinstance(value, list):
			return [cls.wrap(v) for v in value]
		return value


def serialize_chunk(chunk) -> dict:
	if hasattr(chunk, "model_dump"):
		return chunk.model_dump()
	return json.loads(chunk.json())


def record_stream(episode: str, seq: int, model: str, phash: str, stream):
	"""Tee a live stream: yield chunks through unchanged, persist them at the end.
	The record is written even if the consumer stops early (cancel closes the
	generator), so a cancelled recording still replays its consumed prefix."""
	chunks: list[dict] = []
	try:
		for chunk in stream:
			chunks.append(serialize_chunk(chunk))
			yield chunk
	finally:
		append_record(
			episode, {"seq": seq, "kind": "stream", "model": model, "hash": phash, "chunks": chunks}
		)


def replay_call(cfg: dict, model: str, messages: list, expect_stream: bool):
	episode = cfg["episode"]
	seq = next_seq(episode)
	record = load_record(episode, seq)
	if record.get("hash") != prompt_hash(model, messages):
		logger.warning(
			"cassette '%s' call #%d: prompt drifted from the recording (model=%s vs %s) — serving anyway",
			episode,
			seq,
			model,
			record.get("model"),
		)
	if record["kind"] == "stream":
		return iter([Replayed(c) for c in record["chunks"]])
	if record["kind"] == "text":
		return record["content"]
	return Replayed(record["data"])
