from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.artifact import found_photo_list, found_video_list
from builder.ai.agent.tools.images import pexels_clip, run_search_videos

VIDEO = {
	"url": "https://www.pexels.com/video/fishing-boats-at-dawn-10109117/",
	"image": "https://images.pexels.com/videos/10109117/poster.jpeg",
	"duration": 12,
	"user": {"name": "A. Photographer"},
	"video_files": [
		{"file_type": "video/mp4", "width": 3840, "height": 2160, "link": "https://v.example/uhd.mp4"},
		{"file_type": "video/mp4", "width": 960, "height": 540, "link": "https://v.example/sd.mp4"},
		{"file_type": "video/mp4", "width": 1280, "height": 720, "link": "https://v.example/hd.mp4"},
		{"file_type": "video/webm", "width": 1280, "height": 720, "link": "https://v.example/hd.webm"},
	],
}


class TestSearchVideos(FrappeTestCase):
	def test_a_clip_is_its_lightest_hd_mp4_named_by_its_page(self):
		clip = pexels_clip(VIDEO)

		self.assertEqual((clip["url"], clip["size"]), ("https://v.example/hd.mp4", "1280x720"))
		self.assertEqual(clip["description"], "fishing boats at dawn")
		self.assertEqual(clip["poster"], VIDEO["image"])

	def test_a_video_with_no_hd_file_is_left_out(self):
		self.assertIsNone(pexels_clip({**VIDEO, "video_files": VIDEO["video_files"][1:2]}))

	def test_found_footage_reaches_the_generator_apart_from_the_photos(self):
		ctx = SimpleNamespace(found_images=[{"url": "https://p.example/a.jpg", "query": "harbour"}])
		with patch("builder.ai.agent.tools.images.search_pexels_videos", return_value=[pexels_clip(VIDEO)]):
			run_search_videos(ctx, {"query": "boats at dawn"})

		self.assertNotIn("hd.mp4", found_photo_list(ctx))
		self.assertIn("src: https://v.example/hd.mp4", found_video_list(ctx))
		self.assertIn(f"poster: {VIDEO['image']}", found_video_list(ctx))
