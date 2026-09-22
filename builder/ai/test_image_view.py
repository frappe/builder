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

	def test_stops_at_the_per_turn_limit(self, render, _vision):
		ctx = make_ctx()
		for _ in range(MAX_IMAGE_VIEWS_PER_TURN):
			attach_block_images(ctx, IMAGE)

		self.assertEqual(attach_block_images(ctx, IMAGE), "Image view limit reached for this turn.")
