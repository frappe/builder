import base64
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.artifact import read_site_image
from builder.ai.attachments import AttachedImage, TurnImages
from builder.ai.session import AISession

PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
DATA_URL = f"data:image/png;base64,{base64.b64encode(PNG_BYTES).decode()}"


def saved(**kwargs) -> AttachedImage:
	image = AttachedImage(data=DATA_URL, **kwargs)
	image.save()
	return image


def user_row(*urls: str, legacy: bool = False) -> dict:
	if legacy:
		meta = {"attachedImageUrl": urls[0]}
	else:
		meta = {"attachedImages": [{"url": url} for url in urls]} if urls else {}
	return {"role": "user", "content": "hi", "metadata_json": json.dumps(meta)}


class TestAttachedImages(FrappeTestCase):
	def session(self) -> AISession:
		return AISession(frappe.new_doc("Builder AI Session"))

	def test_saved_file_is_private_and_round_trips(self):
		image = saved()
		self.assertTrue(image.url.startswith("/private/files/"))
		content = frappe.get_doc("File", {"file_url": image.url}).get_content()
		if isinstance(content, str):
			content = content.encode()
		self.assertEqual(content, PNG_BYTES)

	def test_bad_data_uri_saves_nothing(self):
		image = AttachedImage(data="data:image/png;base64")
		image.save()
		self.assertEqual(image.url, "")

	def test_request_ignores_a_client_supplied_address(self):
		images = TurnImages.from_request([{"data": DATA_URL, "url": "/private/files/someone-elses.png"}])
		self.assertEqual(images.file_urls(), set())

	def test_request_caps_the_image_count(self):
		with self.assertRaises(frappe.ValidationError):
			TurnImages.from_request([{"data": DATA_URL}] * (TurnImages.MAX_IMAGES + 1))

	def test_request_rejects_a_non_image(self):
		with self.assertRaises(frappe.ValidationError):
			TurnImages.from_request([{"data": "data:video/mp4;base64,AAAA"}])

	def test_parts_label_every_image(self):
		images = TurnImages([saved(), saved(video="demo.mp4", at=64.5)])
		labels = [p["text"] for p in images.parts() if p["type"] == "text"]
		self.assertTrue(labels[0].startswith("Image 1 (saved at /private/files/"))
		self.assertTrue(labels[1].startswith("Frame at 1:04 of demo.mp4"))
		self.assertEqual(sum(p["type"] == "image_url" for p in images.parts()), 2)

	def test_replay_keeps_to_the_image_budget(self):
		limit = AISession.IMAGE_REPLAY_LIMIT
		history = [
			user_row("/files/old.png"),
			user_row(),
			user_row(*[f"/files/{i}.png" for i in range(limit - 1)]),
			{"role": "assistant", "content": "ok", "metadata_json": None},
			user_row("/files/a.png", "/files/b.png"),
		]
		picked = self.session().images_to_replay(history)
		self.assertEqual(set(picked), {2, 4})
		self.assertEqual(len(picked[4]) + len(picked[2]), limit)

	def test_replay_inlines_site_files(self):
		history = [user_row(saved().url)]
		parts = self.session().images_to_replay(history)[0].parts()
		self.assertEqual(parts[-1]["image_url"]["url"], DATA_URL)

	def test_replay_reads_a_legacy_single_image(self):
		for url in (DATA_URL, saved().url):
			parts = self.session().images_to_replay([user_row(url, legacy=True)])[0].parts()
			self.assertEqual(parts[-1]["image_url"]["url"], DATA_URL)

	def test_row_without_image_replays_nothing(self):
		self.assertEqual(self.session().images_to_replay([user_row()]), {})

	def test_private_file_needs_read_permission(self):
		file_url = saved().url
		user = "ai-attachment-perm-test@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Perm"}).insert(
				ignore_permissions=True
			)
		frappe.set_user(user)
		try:
			self.assertIsNone(read_site_image(file_url))
		finally:
			frappe.set_user("Administrator")
		self.assertIsNotNone(read_site_image(file_url))
