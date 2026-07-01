"""Atomic, cross-worker run locks backed by Redis (via frappe.cache()).

The per-session `is_running` DB flag is a non-atomic check-then-set: two requests
can both read 0 and both proceed. These helpers use Redis `SET key val NX EX ttl`
— an atomic acquire that self-heals on worker death when the TTL expires, so a
crashed job can never wedge a page/site forever.

`frappe.cache()` is a `redis.Redis` subclass, so the raw `.set(nx=, ex=)` is used
directly for atomicity (the `set_value` helper has no NX flag). `make_key` scopes
every lock to the current site.

Generic enough to upstream as a `frappe.cache().lock(...)` primitive; Builder is
the first consumer.
"""

from contextlib import contextmanager

import frappe

# TTLs sit just above each job's timeout so a dead worker's lock expires on its own.
SITE_LOCK_TTL = 960  # architect + shared-assets job runs up to ~900s
PAGE_LOCK_TTL = 660  # a single page sub-agent runs up to ~600s


def site_key(folder: str) -> str:
	return f"builder_ai_site_lock:{folder}"


def page_key(page_id: str) -> str:
	return f"builder_ai_page_lock:{page_id}"


def acquire(key: str, ttl: int) -> bool:
	"""Atomically acquire `key`. Returns True if acquired, False if already held."""
	cache = frappe.cache()
	return bool(cache.set(cache.make_key(key), b"1", nx=True, ex=ttl))


def release(key: str) -> None:
	frappe.cache().delete_value(key)


@contextmanager
def guard(key: str, ttl: int):
	"""Context manager that yields True only if the lock was acquired, releasing on
	exit. Use for the happy path where you hold the lock for the whole block:

	    with guard(page_key(pid), PAGE_LOCK_TTL) as got:
	        if not got:
	            return  # someone else is already running this
	        ...work...
	"""
	got = acquire(key, ttl)
	try:
		yield got
	finally:
		if got:
			release(key)
