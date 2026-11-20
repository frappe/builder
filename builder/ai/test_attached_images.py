import base64
import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.artifact import read_site_image
from builder.ai.attachments import AttachedImage, TurnImages
from builder.ai.block_codec import BlockCodec
from builder.ai.session import AISession

PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
DATA_URL = f"data:image/png;base64,{base64.b64encode(PNG_BYTES).decode()}"


def saved(**kwargs) -> AttachedImage:
	image = AttachedImage(data=DATA_URL, **kwargs)
	image.save()
	return image


def make_user(email: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Perm"}).insert(
			ignore_permissions=True
		)
	return email


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

	def test_request_takes_only_the_image_types_models_read(self):
		payload = base64.b64encode(PNG_BYTES).decode()
		for kind in ("svg+xml", "html", "x-icon", ""):
			with self.subTest(kind=kind), self.assertRaises(frappe.ValidationError):
				TurnImages.from_request([{"data": f"data:image/{kind};base64,{payload}"}])
		for kind in ("png", "jpeg", "webp", "gif"):
			self.assertTrue(TurnImages.from_request([{"data": f"data:image/{kind};base64,{payload}"}]))

	def test_saved_file_is_named_by_its_image_type(self):
		# bytes of its own: a File with the same content as an earlier one gets that one's address
		content = base64.b64encode(PNG_BYTES + frappe.generate_hash(length=8).encode()).decode()
		image = AttachedImage(data=f"data:image/png;charset=utf-8;base64,{content}")
		image.save()
		self.assertTrue(image.url.endswith(".png"), image.url)

	def test_parts_label_every_image(self):
		images = TurnImages([saved(), saved(video="demo.mp4", at=64.5)])
		labels = [p["text"] for p in images.parts() if p["type"] == "text"]
		self.assertTrue(labels[0].startswith("Image 1 (saved at /private/files/"))
		self.assertTrue(labels[1].startswith("Frame at 1:04 of demo.mp4"))
		self.assertEqual(sum(p["type"] == "image_url" for p in images.parts()), 2)

	def test_a_frame_time_that_is_no_time_in_a_video_is_dropped(self):
		for at in (float("inf"), float("-inf"), float("nan"), -1, 10**9, True, "12"):
			with self.subTest(at=at):
				image = AttachedImage.from_dict({"url": "/files/a.png", "video": "demo.mp4", "at": at})
				self.assertIsNone(image.at)
				self.assertEqual(image.label(1), "Frame at 0:00 of demo.mp4 (saved at /files/a.png)")
		self.assertEqual(AttachedImage.from_dict({"video": "demo.mp4", "at": 64.5}).at, 64.5)

	def test_a_message_stored_with_an_infinite_frame_time_still_replays(self):
		# JSON carries Infinity both ways: a request's body, and a message's metadata as it was stored
		meta = json.dumps({"attachedImages": [{"url": saved().url, "video": "demo.mp4", "at": float("inf")}]})
		history = [{"role": "user", "content": "hi", "metadata_json": meta}]
		parts = self.session().images_to_replay(history)[0].parts()
		self.assertTrue(parts[0]["text"].startswith("Frame at 0:00 of demo.mp4"))
		self.assertEqual(parts[1]["image_url"]["url"], DATA_URL)

	def test_the_job_gets_a_saved_image_by_its_address_and_reads_it_back(self):
		unsaved = AttachedImage(data=DATA_URL)  # its save failed: the job has nothing else to read
		payload = TurnImages([saved(), unsaved]).payload()
		self.assertNotIn("data", payload[0])
		self.assertEqual(payload[1]["data"], DATA_URL)
		parts = TurnImages.from_payload(payload).parts()
		self.assertEqual([p["image_url"]["url"] for p in parts if p["type"] == "image_url"], [DATA_URL] * 2)

	def test_an_image_as_large_as_a_message_takes_is_read_back_from_its_file(self):
		# past the 3 MB replay used to read back, within what a request takes (about 5.25 MB)
		content = base64.b64encode(PNG_BYTES + os.urandom(3_500_000)).decode()
		data = BlockCodec.validate_image_data(f"data:image/png;base64,{content}")
		image = AttachedImage(data=data)
		image.save()
		self.assertEqual(read_site_image(image.url), data)
		[part] = [
			p for p in TurnImages.from_payload(TurnImages([image]).payload()).parts() if "image_url" in p
		]
		self.assertEqual(part["image_url"]["url"], data)

	def test_an_image_another_user_sent_too_is_read_through_this_user_s_own_file(self):
		# the same bytes share one address, whoever sent them first
		content = base64.b64encode(PNG_BYTES + frappe.generate_hash(length=8).encode()).decode()
		data = f"data:image/png;base64,{content}"
		urls = {}
		try:
			for user in ("ai-attachment-first@example.com", "ai-attachment-second@example.com"):
				frappe.set_user(make_user(user))
				image = AttachedImage(data=data)
				image.save()
				urls[user] = image.url
			for user in urls:
				frappe.set_user(user)
				self.assertEqual(read_site_image(urls[user]), data, user)
		finally:
			frappe.set_user("Administrator")

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
		frappe.set_user(make_user("ai-attachment-perm-test@example.com"))
		try:
			self.assertIsNone(read_site_image(file_url))
		finally:
			frappe.set_user("Administrator")
		self.assertIsNotNone(read_site_image(file_url))
