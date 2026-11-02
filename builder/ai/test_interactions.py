import unittest

from builder.ai.browser_check import validate_interactions


class TestInteractionBoundary(unittest.TestCase):
	def test_rejects_unbounded_or_executable_steps(self):
		for steps in (
			[{"action": "evaluate", "selector": "body"}],
			[{"action": "click", "selector": "body"}] * 17,
		):
			with self.subTest(steps=steps), self.assertRaises(ValueError):
				validate_interactions(steps)

	def test_requires_declared_assertions_and_navigation_keys(self):
		for step in (
			{"action": "assert", "selector": "body", "state": "anything"},
			{"action": "assert", "selector": "body", "state": "attribute", "value": "true"},
			{"action": "press", "selector": "button", "key": "F5"},
			{"action": "fill", "selector": "input", "value": "x" * 1001},
		):
			with self.subTest(step=step), self.assertRaises(ValueError):
				validate_interactions([step])
