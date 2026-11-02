import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from builder.ai.budgets import ContextBudgetError, ModelCapabilityError, TurnBudgetError, begin_attempt
from builder.ai.llm import user_facing_error
from builder.ai.workflow import ModelRequest


class TestTurnBudget(unittest.TestCase):
	def setUp(self):
		self.ctx = SimpleNamespace(usage={"reserved_tokens": 272036})
		self.request = ModelRequest(
			"test/model", [{"role": "user", "content": "Continue"}], {"max_tokens": 16000}
		)
		self.contract = {"context": 500000, "output": None, "tools": True, "streaming": True}
		self.capabilities = patch("builder.ai.budgets.ModelRegistry.capabilities", return_value=self.contract)
		self.capabilities.start()
		self.addCleanup(self.capabilities.stop)

	def test_failed_tenth_round_fits_the_new_default(self):
		with (
			patch.dict(frappe.conf, {"bob_run_token_budget": None}),
			patch("builder.ai.budgets.estimate_tokens", return_value=15514),
		):
			begin_attempt(self.ctx, self.request, "coordinator")
		self.assertEqual(self.ctx.usage["reserved_tokens"], 303550)
		self.assertEqual(self.ctx.usage["token_budget"], 1000000)

	def test_default_limit_and_explicit_overrides_still_stop_before_the_next_call(self):
		for configured, used in [(None, 970000), (300000, 272036)]:
			with (
				self.subTest(configured=configured),
				patch.dict(frappe.conf, {"bob_run_token_budget": configured}),
				patch("builder.ai.budgets.estimate_tokens", return_value=15514),
			):
				self.ctx.usage = {"reserved_tokens": used}
				with self.assertRaises(TurnBudgetError):
					begin_attempt(self.ctx, self.request, "coordinator")
				self.assertEqual(self.ctx.usage["reserved_tokens"], used)
				self.assertNotIn("ledger", self.ctx.usage)

	def test_turn_budget_does_not_expand_the_model_context(self):
		self.contract.update(context=8192, output=2048)
		with patch("builder.ai.budgets.estimate_tokens", return_value=40000):
			with self.assertRaises(ContextBudgetError) as error:
				begin_attempt(self.ctx, self.request, "coordinator")
		self.assertNotIsInstance(error.exception, TurnBudgetError)
		self.assertEqual(self.ctx.usage["reserved_tokens"], 272036)

	def test_errors_distinguish_the_limit_without_exposing_exception_text(self):
		for error, expected in [
			(TurnBudgetError, "Bob's token budget"),
			(ContextBudgetError, "model's context"),
			(ModelCapabilityError, "tool or streaming support"),
		]:
			message = user_facing_error(error("private provider detail"))
			self.assertIn(expected, message)
			self.assertNotIn("private provider detail", message)
