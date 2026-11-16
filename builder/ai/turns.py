"""How a site's AI turns are queued, so one site can't hold back the rest of a bench.

A turn runs as a background job, and someone is watching the chat, so it goes to the front of the
queue, ahead of the scheduler's backlog. A bench's queue can serve many sites (frappe.page runs every
site on one), so two limits keep a site from taking it over:
- A site has at most `builder_ai_turns_in_flight` turns (site config, default 3) queued or running at
  once. Each holds a ticket from when it is queued until its job ends. A ticket also lapses on its own
  once its job could no longer be waiting or running, so a worker that died frees it.
- Only FRONT_TURNS of a site's turns in each FRONT_WINDOW go to the front. The rest queue behind
  what is already waiting, so a site sending turn after turn can't keep everyone else waiting.

Turns go to the RQ queue `builder_ai_queue` names (site config, default "default"). A bench that serves
many sites gives them one of their own, so AI turns and every other background job stop waiting on each
other: declare it in common_site_config.json (`"workers": {"<name>": {"timeout": 3660}}`) and run a
worker for it alone (`bench worker --queue <name>`). A name no worker config declares falls back to
"default", which every bench has.
"""

import secrets
import time

import frappe
from frappe import _
from frappe.utils import cint

DEFAULT_TURNS_IN_FLIGHT = 3
QUEUE_CONFIG = "builder_ai_queue"
DEFAULT_QUEUE = "default"
FRONT_TURNS = 10
FRONT_WINDOW = 10 * 60
# how long a turn may wait for a worker before its ticket lapses anyway
QUEUE_WAIT = 15 * 60
TICKETS_KEY = "builder_ai_turn_tickets"
FRONT_KEY = "builder_ai_turns_at_front"

# The count and the claim are one step, so turns sent side by side can't both take the last ticket.
CLAIM = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
	return 0
end
redis.call('ZADD', KEYS[1], ARGV[3], ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""
COUNT_FRONT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
	redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class TurnQueue:
	@classmethod
	def claim(cls, job_timeout: int) -> str | None:
		"""A ticket for one more turn, or None when the site has as many queued or running as it may.
		The ticket goes back if the transaction that took it rolls back."""
		ticket = secrets.token_hex(8)
		now = time.time()
		lapses = now + job_timeout + QUEUE_WAIT
		args = (now, cls.limit(), lapses, ticket, int(lapses - now))
		if not cint(frappe.cache.eval(CLAIM, 1, cls.key(TICKETS_KEY), *args)):
			return None
		frappe.db.after_rollback.add(lambda: cls.release(ticket))
		return ticket

	@classmethod
	def take_over(cls, ticket: str, job_timeout: int) -> str:
		"""Keep a running turn's ticket for the turn it queues next, which needs no free one."""
		lapses = time.time() + job_timeout + QUEUE_WAIT
		frappe.cache.zadd(cls.key(TICKETS_KEY), {ticket: lapses})
		frappe.cache.expire(cls.key(TICKETS_KEY), job_timeout + QUEUE_WAIT)
		frappe.db.after_rollback.add(lambda: cls.release(ticket))
		return ticket

	@classmethod
	def release(cls, ticket: str | None) -> None:
		if ticket:
			frappe.cache.zrem(cls.key(TICKETS_KEY), ticket)

	@classmethod
	def enqueue(cls, ticket: str, job_timeout: int, **job) -> None:
		"""Queue a turn's job holding `ticket`, after the request commits."""
		from builder.ai.agent.loop import run_agent_job

		frappe.enqueue(
			run_agent_job,
			queue=cls.queue(),
			at_front=cls.goes_first(),
			timeout=job_timeout,
			enqueue_after_commit=True,
			turn_ticket=ticket,
			**job,
		)

	@classmethod
	def goes_first(cls) -> bool:
		count = frappe.cache.eval(COUNT_FRONT, 1, cls.key(FRONT_KEY), FRONT_WINDOW)
		return cint(count) <= FRONT_TURNS

	@classmethod
	def in_flight(cls) -> int:
		return frappe.cache.zcount(cls.key(TICKETS_KEY), time.time(), "+inf")

	@staticmethod
	def queue() -> str:
		"""The queue AI turns go to: `builder_ai_queue`, when the bench declares it."""
		from frappe.utils.background_jobs import get_queues_timeout

		name = (frappe.conf.get(QUEUE_CONFIG) or DEFAULT_QUEUE).strip()
		if name in get_queues_timeout():
			return name
		frappe.logger("builder.ai.turns").error(
			f"{QUEUE_CONFIG} names the queue {name!r}, which no `workers` config declares: using {DEFAULT_QUEUE!r}"
		)
		return DEFAULT_QUEUE

	@staticmethod
	def limit() -> int:
		return cint(frappe.conf.get("builder_ai_turns_in_flight")) or DEFAULT_TURNS_IN_FLIGHT

	@staticmethod
	def key(name: str) -> str:
		# scoped to the site, like every other cache key
		return frappe.cache.make_key(name)

	@classmethod
	def busy_message(cls) -> str:
		return _(
			"Bob is already working on {0} requests on this site. Try again once one of them is done."
		).format(cls.limit())
