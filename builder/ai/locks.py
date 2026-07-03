"""Atomic, cross-worker run locks backed by Redis (via frappe.cache()).

Acquire uses `SET key token NX EX ttl` — atomic, and self-healing when a worker
dies (the TTL expires, so a crashed job can never wedge a page/session forever).
The returned token FENCES release: a worker that outlived its TTL can no longer
delete the lock a newer holder acquired (release compares the token in Redis).

`frappe.cache()` is a `redis.Redis` subclass, so the raw `.set(nx=, ex=)` is used
directly for atomicity (the `set_value` helper has no NX flag). `make_key` scopes
every lock to the current site.

Generic enough to upstream as a `frappe.cache().lock(...)` primitive; Builder is
the first consumer.
"""

import secrets
from contextlib import contextmanager

import frappe

# TTLs sit just above each holder's job timeout so a dead worker's lock expires
# on its own. Page locks can be held by a dashboard turn (timeout 1200s); task
# locks by a fan-out sub-agent (timeout 780s); session locks by any turn.
PAGE_LOCK_TTL = 1260
TASK_LOCK_TTL = 840
SESSION_LOCK_TTL = 1260

RELEASE_IF_TOKEN_MATCHES = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end
return 0
"""


def page_key(page_id: str) -> str:
	return f"builder_ai_page_lock:{page_id}"


def task_key(task_id: str) -> str:
	"""Lock for a page-less fan-out task (page-backed tasks use page_key instead)."""
	return f"builder_ai_task_lock:{task_id}"


def session_key(session_id: str) -> str:
	"""One running turn per chat session (replaces the old is_running DB flag,
	which was a non-atomic check-then-set and needed manual repair after a crash)."""
	return f"builder_ai_session_lock:{session_id}"


def acquire(key: str, ttl: int) -> str | None:
	"""Atomically acquire `key`. Returns the release token, or None if already held."""
	token = secrets.token_hex(8)
	cache = frappe.cache()
	return token if cache.set(cache.make_key(key), token, nx=True, ex=ttl) else None


def release(key: str, token: str | None) -> None:
	"""Release `key` only if we still hold it (token match) — never a newer holder's lock."""
	if not token:
		return
	cache = frappe.cache()
	cache.eval(RELEASE_IF_TOKEN_MATCHES, 1, cache.make_key(key), token)


def held(key: str) -> bool:
	cache = frappe.cache()
	return bool(cache.exists(cache.make_key(key)))


@contextmanager
def guard(key: str, ttl: int):
	"""Yield the lock token (None if not acquired), releasing on exit:

	with guard(page_key(pid), PAGE_LOCK_TTL) as got:
	    if not got:
	        return  # someone else is already running this
	    ...work...
	"""
	token = acquire(key, ttl)
	try:
		yield token
	finally:
		release(key, token)
