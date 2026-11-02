import base64
from contextlib import ExitStack
from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.preview import preview_page, render_page_image
from builder.html_preview_image import preview_regions, render_full_page


class TestAgentPreview(FrappeTestCase):
	def test_renders_desktop_only(self):
		page = Mock()
		page.get_preview_html.return_value = "<p>Hi</p>"
		with patch("builder.html_preview_image.render_full_page", return_value=b"preview") as render:
			self.assertEqual(render_page_image(page, "dark"), b"preview")

		self.assertNotIn("viewport", preview_page.parameters["properties"])
		page.get_preview_html.assert_called_once_with(color_scheme="dark")
		render.assert_called_once_with("<p>Hi</p>", width=1280, height=900)


class TestFullPagePreview(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.generator = Mock(_devtools_url=None)
		self.generator._set_devtools_url.side_effect = lambda: setattr(
			self.generator, "_devtools_url", "ws://browser"
		)
		self.session = Mock()
		self.session.send.return_value = ({"browserContextId": "context"}, None)
		self.page = Mock()
		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		self.stack.enter_context(
			patch("frappe.utils.chromium.ChromiumManager.acquire", return_value=(self.generator, "browser"))
		)
		self.socket = self.stack.enter_context(
			patch("frappe.utils.chromium.CDPSocketClient", return_value=self.session)
		)
		self.stack.enter_context(patch("frappe.utils.chromium.Page", return_value=self.page))
		self.stack.enter_context(patch("frappe.utils.pdf.get_host_url", return_value="http://builder.test"))

	def test_captures_full_document_with_clipped_regions_and_closes_browser(self):
		self.page.send.side_effect = [
			({"cssContentSize": {"height": 2400}}, None),
			({"data": base64.b64encode(b"preview").decode()}, None),
		]
		regions = []
		with patch(
			"builder.html_preview_image.preview_regions",
			return_value=[{"label": "Contact", "box": (0, 1200, 500, 1600)}],
		) as find_regions:
			image = render_full_page(
				"<section>Contact</section>", width=1000, height=700, max_height=1800, regions=regions
			)

		self.assertEqual(image, b"preview")
		self.assertEqual(regions, [{"label": "Contact", "box": (0, 1200, 500, 1600)}])
		find_regions.assert_called_once_with(self.page, 1000, 1800)
		self.page.set_device_metrics.assert_called_once_with(1000, 700)
		self.page.set_tab_url.assert_called_once_with("http://builder.test")
		self.assertEqual(self.page.send.call_args_list[1].args[1]["clip"]["height"], 1800)
		self.socket.assert_called_once_with("ws://browser")
		self.page.close.assert_called_once()
		self.session.disconnect.assert_called_once()
		self.generator.remove_browser.assert_called_once_with("browser")

	def test_capture_failure_still_closes_page_session_and_browser(self):
		self.page.send.side_effect = [
			({"contentSize": {"height": 1200}}, None),
			({}, {"message": "capture failed"}),
		]
		with self.assertRaisesRegex(RuntimeError, "Could not capture screenshot"):
			render_full_page("<p>Hi</p>")

		self.page.close.assert_called_once()
		self.session.disconnect.assert_called_once()
		self.generator.remove_browser.assert_called_once_with("browser")


class TestPreviewRegions(FrappeTestCase):
	def test_evaluation_error_returns_no_regions(self):
		page = Mock()
		page.send.return_value = ({"exceptionDetails": {"text": "bad script"}}, None)

		self.assertEqual(preview_regions(page, 1000, 1800), [])
		self.assertEqual(page.send.call_args.args[0], "Runtime.evaluate")
