import base64
import sys
from contextlib import ExitStack
from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.preview import render_page_image
from builder.html_preview_image import render_full_page


class TestRenderPageImage(FrappeTestCase):
	def test_renders_from_a_real_viewport_size(self):
		page = Mock()
		page.get_preview_html.return_value = "<p>Hi</p>"
		with patch("builder.html_preview_image.render_full_page", return_value=b"preview") as render:
			self.assertEqual(render_page_image(page, "mobile", "dark"), b"preview")

		page.get_preview_html.assert_called_once_with(color_scheme="dark")
		render.assert_called_once_with("<p>Hi</p>", width=390, height=844, max_height=8000)


class TestFullPageCapture(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.generator = Mock(_devtools_url=None, _chromium_process=None)
		self.generator._set_devtools_url.side_effect = lambda: setattr(
			self.generator, "_devtools_url", "ws://browser"
		)
		self.session = Mock()
		self.session.send.return_value = ({"browserContextId": "context"}, None)
		self.page = Mock()
		stack = ExitStack()
		self.addCleanup(stack.close)
		stack.enter_context(
			patch("frappe.utils.chromium.ChromiumManager.acquire", return_value=(self.generator, "browser"))
		)
		stack.enter_context(patch("frappe.utils.chromium.CDPSocketClient", return_value=self.session))
		stack.enter_context(patch("frappe.utils.chromium.Page", return_value=self.page))
		stack.enter_context(patch("frappe.utils.pdf.get_host_url", return_value="http://builder.test"))

	def assert_cleaned_up(self):
		self.page.close.assert_called_once()
		self.session.disconnect.assert_called_once()
		self.generator.remove_browser.assert_called_once_with("browser")

	def test_captures_the_document_below_the_viewport(self):
		self.page.send.side_effect = [
			({"cssContentSize": {"height": 2400}}, None),
			({"data": base64.b64encode(b"preview").decode()}, None),
		]

		image = render_full_page("<p>Hi</p>", width=1280, height=900, max_height=8000)

		self.assertEqual(image, b"preview")
		self.page.set_device_metrics.assert_called_once_with(1280, 900)
		params = self.page.send.call_args_list[1].args[1]
		self.assertTrue(params["captureBeyondViewport"])
		self.assertEqual(params["clip"]["height"], 2400)
		self.assert_cleaned_up()

	def test_caps_a_very_long_document(self):
		self.page.send.side_effect = [
			({"contentSize": {"height": 20000}}, None),
			({"data": base64.b64encode(b"preview").decode()}, None),
		]

		render_full_page("<p>Hi</p>", max_height=8000)

		self.assertEqual(self.page.send.call_args_list[1].args[1]["clip"]["height"], 8000)

	def test_a_failed_measure_still_closes_the_browser(self):
		self.page.send.return_value = ({}, {"message": "no layout"})

		with self.assertRaisesRegex(RuntimeError, "Error measuring the page"):
			render_full_page("<p>Hi</p>")

		self.assert_cleaned_up()

	def test_a_failed_capture_resets_a_crashed_chrome(self):
		self.generator._chromium_process = Mock(**{"poll.return_value": 1})
		self.page.send.side_effect = [({"contentSize": {"height": 1200}}, None), ({}, {"message": "crashed"})]

		with self.assertRaisesRegex(RuntimeError, "Error capturing screenshot"):
			render_full_page("<p>Hi</p>")

		self.assert_cleaned_up()
		self.generator._close_browser.assert_called_once()

	def test_a_failed_context_leaves_a_running_chrome_alone(self):
		self.generator._chromium_process = Mock(**{"poll.return_value": None})
		self.session.send.return_value = ({}, {"message": "no context"})

		with self.assertRaisesRegex(RuntimeError, "Error creating browser context"):
			render_full_page("<p>Hi</p>")

		self.generator._close_browser.assert_not_called()

	def test_falls_back_to_a_tall_viewport_without_chromium_helpers(self):
		with (
			patch.dict(sys.modules, {"frappe.utils.chromium": None}),
			patch("builder.html_preview_image.render", return_value=b"tall") as render,
		):
			self.assertEqual(render_full_page("<p>Hi</p>", width=390, height=844, max_height=8000), b"tall")

		render.assert_called_once_with("<p>Hi</p>", width=390, height=8000)
