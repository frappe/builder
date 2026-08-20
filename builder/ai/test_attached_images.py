import base64
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.artifact import read_site_image
from builder.ai.api import save_attached_image
from builder.ai.session import AISession

PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
DATA_URL = f"data:image/png;base64,{base64.b64encode(PNG_BYTES).decode()}"


def user_row(image_url: str | None = None) -> dict:
	meta = {"attachedImageUrl": image_url} if image_url else {}
	return {"role": "user", "content": "hi", "metadata_json": json.dumps(meta)}


class TestAttachedImages(FrappeTestCase):
	def session(self) -> AISession:
		return AISession(frappe.new_doc("Builder AI Session"))

	def test_saved_file_is_private_and_round_trips(self):
		file_url = save_attached_image(DATA_URL)
		self.assertTrue(file_url.startswith("/private/files/"))
		content = frappe.get_doc("File", {"file_url": file_url}).get_content()
		if isinstance(content, str):
			content = content.encode()
		self.assertEqual(content, PNG_BYTES)

	def test_bad_data_uri_saves_nothing(self):
		self.assertIsNone(save_attached_image("data:image/png;base64"))

	def test_replay_picks_newest_images_only(self):
		history = [
			user_row(DATA_URL),
			user_row(),
			user_row("/files/a.png"),
			{"role": "assistant", "content": "ok", "metadata_json": None},
			user_row("/files/b.png"),
		]
		self.assertEqual(self.session().image_rows_to_replay(history), {2, 4})

	def test_replay_part_inlines_site_file(self):
		file_url = save_attached_image(DATA_URL)
		part = self.session().replay_image_part(user_row(file_url))
		self.assertEqual(part["image_url"]["url"], DATA_URL)

	def test_replay_part_passes_legacy_data_uri(self):
		part = self.session().replay_image_part(user_row(DATA_URL))
		self.assertEqual(part["image_url"]["url"], DATA_URL)

	def test_row_without_image_replays_nothing(self):
		self.assertIsNone(self.session().replay_image_part(user_row()))

	def test_private_file_needs_read_permission(self):
		file_url = save_attached_image(DATA_URL)
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
