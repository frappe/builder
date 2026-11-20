import base64
import sys
from contextlib import ExitStack
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.loop import AgentRunner
from builder.ai.agent.tools.preview import attach_block_images, render_page_image, run_preview_page
from builder.ai.test_page_changes import heading, make_page
from builder.builder.doctype.builder_page.builder_page import BuilderPage
from builder.builder.tests.hosting_hooks import hosting_hooks, isolate, page_tools, preview_tools
from builder.html_preview_image import render, render_full_page


class TestRenderPageImage(FrappeTestCase):
	def test_renders_from_a_real_viewport_size(self):
		page = Mock()
		page.get_preview_html.return_value = "<p>Hi</p>"
		with patch("builder.html_preview_image.render_full_page", return_value=b"preview") as render:
			self.assertEqual(render_page_image(page, "mobile", "dark"), b"preview")

		page.get_preview_html.assert_called_once_with(color_scheme="dark")
		render.assert_called_once_with(
			"<p>Hi</p>", width=390, height=844, max_height=8000, block_external=False
		)


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

	def test_off_the_web_chromium_fails_what_is_not_on_this_site(self):
		"""Frappe's interceptor then fails every request off the host instead of fetching it"""
		self.page.send.side_effect = lambda *args: ({"contentSize": {"height": 900}, "data": ""}, None)

		render_full_page("<p>Hi</p>")
		self.assertIs(self.page.block_external_requests, False)

		render_full_page("<p>Hi</p>", block_external=True)
		self.assertIs(self.page.block_external_requests, True)

	def test_off_the_web_no_renderer_that_fetches_or_sends_the_page_out_is_used(self):
		with (
			patch.dict(sys.modules, {"frappe.utils.chromium": None}),
			patch("builder.html_preview_image.render_via_service") as service,
			self.assertRaisesRegex(RuntimeError, "off the web"),
		):
			render("<p>Hi</p>", block_external=True)

		service.assert_not_called()

	def test_a_viewport_render_off_the_web_is_one_screenful_of_the_blocking_capture(self):
		with patch("builder.html_preview_image.render_full_page", return_value=b"thumb") as full_page:
			self.assertEqual(render("<p>Hi</p>", width=1280, height=720, block_external=True), b"thumb")

		full_page.assert_called_once_with(
			"<p>Hi</p>", width=1280, height=720, max_height=720, block_external=True
		)


class TestPreviewOffTheWeb(FrappeTestCase):
	"""A hosting app that withholds Bob's web tools (frappe.page's own site) keeps its server off the web, and
	its pages load nothing from outside: the screenshots Bob takes and the page thumbnails fetch nothing either."""

	def setUp(self):
		super().setUp()
		self.page_id = make_page("Studio", f"pv-{frappe.generate_hash(length=6)}", [heading("pvhead", "Hi")])

	def blocking(self, runner) -> bool:
		with (
			patch("builder.html_preview_image.render_full_page", return_value=b"webp") as full_page,
			patch("builder.ai.agent.tools.preview.refresh_page_thumbnail"),
		):
			run_preview_page(runner, {})
		return full_page.call_args.kwargs["block_external"]

	def test_bobs_screenshot_fetches_nothing_from_outside_off_the_web(self):
		with hosting_hooks(builder_agent_tools=[page_tools, preview_tools]):
			kept_off = AgentRunner("hi", model="m", api_key="k", page_id=self.page_id)
		with hosting_hooks(builder_agent_tools=[]):
			anywhere = AgentRunner("hi", model="m", api_key="k", page_id=self.page_id)

		self.assertTrue(self.blocking(kept_off))
		self.assertFalse(self.blocking(anywhere))

	def test_a_web_image_is_not_fetched_for_bob_to_view_off_the_web(self):
		with hosting_hooks(builder_agent_tools=[page_tools]):
			runner = AgentRunner("hi", model="m", api_key="k", page_id=self.page_id)
		block = {"element": "img", "attributes": {"src": "https://images.example.com/hero.png"}}

		with (
			patch("builder.ai.models.ModelRegistry.supports_vision", return_value=True),
			patch("builder.ai.agent.tools.web.fetch_public") as fetch,
			patch("builder.html_preview_image.render") as image,
		):
			out = attach_block_images(runner, block)

		self.assertIn("can't be shown to you", out)
		fetch.assert_not_called()
		image.assert_not_called()

	def test_an_isolated_sites_page_thumbnail_fetches_nothing_from_outside(self):
		page = Mock(name="page")

		def thumbnail(*hooks) -> bool:
			with (
				hosting_hooks(builder_is_isolated=list(hooks)),
				patch(
					"builder.builder.doctype.builder_page.builder_page.get_builder_page_preview_file_paths",
					return_value=("/files/p.webp", "/tmp/p.webp"),
				),
				patch("builder.builder.doctype.builder_page.builder_page.generate_preview") as generate,
			):
				BuilderPage.generate_page_preview_image(page, html="<p>Hi</p>")
			return generate.call_args.kwargs["block_external"]

		self.assertTrue(thumbnail(isolate))
		self.assertFalse(thumbnail())


class TestPreviewPageErrors(FrappeTestCase):
	def test_a_page_that_raises_says_why_instead_of_blaming_the_renderer(self):
		import frappe

		from builder.ai.agent.tools.preview import run_preview_page

		page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Broken Data Page"}).insert()
		page.db_set(
			"page_data_script", "rows = [1]\ndef count():\n    return len(rows)\ndata.total = count()"
		)
		ctx = Mock(page_id=page.name, preview_count=0)

		out = run_preview_page(ctx, {})

		self.assertTrue(out.startswith("FAILED: the page itself fails to render"), out)
		self.assertIn("NameError", out)
		self.assertIn("line 3", out)
		self.assertEqual(ctx.preview_count, 0)
