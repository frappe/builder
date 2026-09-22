from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.preview import MAX_IMAGE_VIEWS_PER_TURN, attach_block_images

IMAGE = {"element": "img", "attributes": {"src": "/files/light.png", "darkSrc": "/files/dark.svg"}}


def make_ctx():
	return SimpleNamespace(loop_model="vision-model", image_views=0, pending_images=[])


@patch("builder.ai.models.ModelRegistry.supports_vision", return_value=True)
@patch("builder.html_preview_image.render", return_value=b"webp")
class TestImageView(FrappeTestCase):
	def test_attaches_the_image_and_its_dark_mode_version(self, render, _vision):
		ctx = make_ctx()

		out = attach_block_images(ctx, IMAGE)

		self.assertEqual(out, "Attached below: the block's image and dark-mode image.")
		self.assertEqual(len(ctx.pending_images), 2)
		self.assertIn('src="/files/dark.svg"', render.call_args.args[0])

	def test_skips_a_block_without_an_image(self, render, _vision):
		out = attach_block_images(make_ctx(), {"element": "div", "attributes": {}})

		self.assertEqual(out, "This block has no image to show.")
		render.assert_not_called()

	def test_refuses_an_internal_address(self, render, _vision):
		block = {"element": "img", "attributes": {"src": "http://127.0.0.1:8000/admin.png"}}

		out = attach_block_images(make_ctx(), block)

		self.assertIn("private, internal or unreachable", out)
		render.assert_not_called()

	def test_inlines_a_remote_image_instead_of_letting_the_renderer_fetch_it(self, render, _vision):
		response = SimpleNamespace(
			status_code=200,
			headers={"content-type": "image/png"},
			raw=SimpleNamespace(read=lambda size, decode_content: b"png-bytes"),
		)
		block = {"element": "img", "attributes": {"src": "https://images.example.com/hero.png"}}

		with patch("builder.ai.agent.tools.web.fetch_public", return_value=(response, "")):
			attach_block_images(make_ctx(), block)

		rendered = render.call_args.args[0]
		self.assertIn("data:image/png;base64,", rendered)
		self.assertNotIn("images.example.com", rendered)

	def test_attaches_nothing_when_one_render_fails(self, render, _vision):
		render.side_effect = [b"webp", RuntimeError("renderer down")]
		ctx = make_ctx()

		out = attach_block_images(ctx, IMAGE)

		self.assertIn("could not be rendered", out)
		self.assertEqual(ctx.pending_images, [])

	def test_stops_at_the_per_turn_limit(self, render, _vision):
		ctx = make_ctx()
		for _ in range(MAX_IMAGE_VIEWS_PER_TURN):
			attach_block_images(ctx, IMAGE)

		self.assertEqual(attach_block_images(ctx, IMAGE), "Image view limit reached for this turn.")
