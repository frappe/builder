import json

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner


class TestTraceRedaction(FrappeTestCase):
	def recorded_args(self, args: dict) -> str:
		runner = AgentRunner("hi", model="m", api_key="k")
		runner.record_round(0, [{"tool_name": "write_page_data_script", "args": args}], "")
		return runner.trace[0]["tools"][0]["args"]

	def test_keeps_credentials_out_of_the_saved_trace(self):
		script = 'client = FrappeClient("https://x.io", api_key="b478a32c", api_secret="e292f174")'

		saved = self.recorded_args({"script": script, "headers": {"Authorization": "token abc:def"}})

		for secret in ("b478a32c", "e292f174", "abc:def"):
			self.assertNotIn(secret, saved)
		self.assertIn('api_key=\\"[redacted]', saved)

	def test_leaves_ordinary_args_alone(self):
		args = {"token_name": "brand-ink", "value": "#111111", "script": "const secretSauce = 1;"}

		self.assertEqual(self.recorded_args(args), json.dumps(args))
