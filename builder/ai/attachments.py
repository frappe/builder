"""Images the user attaches to one chat turn.

The editor sends pasted or picked images, and frames it sampled from an attached
video: few models Bob drives read video, but every vision model reads its frames.
"""

import logging

import frappe
from frappe import _

from builder.ai.block_codec import BlockCodec

logger = frappe.logger("builder.ai.attachments")
logger.setLevel(logging.INFO)


class AttachedImage:
	def __init__(self, data: str = "", url: str = "", video: str = "", at: float | None = None):
		self.data = data  # the data URI, only on the turn it was sent
		self.url = url  # the saved file, or a legacy inline data URI
		self.video = video
		self.at = at

	@classmethod
	def from_dict(cls, d: dict) -> "AttachedImage":
		at = d.get("at") if isinstance(d.get("at"), int | float) else None
		return cls(d.get("data") or "", d.get("url") or "", str(d.get("video") or "")[:140], at)

	def to_dict(self, with_data: bool = False) -> dict:
		d = {"url": self.url or self.data}
		if with_data:
			d["data"] = self.data
		if self.video:
			d.update(video=self.video, at=self.at)
		return d

	def label(self, number: int) -> str:
		name = f"Frame at {self.timestamp()} of {self.video}" if self.video else f"Image {number}"
		return f"{name} (saved at {self.url})" if self.url.startswith("/") else name

	def timestamp(self) -> str:
		seconds = int(float(self.at or 0))
		return f"{seconds // 60}:{seconds % 60:02d}"

	def save(self) -> None:
		"""Persist as a site file. The data URI only lives for the turn it was sent on;
		the file is what later turns replay and briefs reference. Private: it belongs
		to the chat (a mock may be confidential), and every reader — replay, brief
		attachment, the chat thumbnail — goes through permissioned paths."""
		try:
			header, content = self.data.split(";base64,", 1)
			ext = header.removeprefix("data:image/").split("+")[0] or "png"
			file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"ai-attachment-{frappe.generate_hash(length=10)}.{ext}",
					"is_private": 1,
					"folder": "Home/Builder Uploads",
					"content": content,
					"decode": True,
				}
			).insert(ignore_permissions=True)
			self.url = file.file_url
		except Exception:
			logger.warning("could not save the attached image as a file", exc_info=True)

	def inline_url(self) -> str | None:
		"""What a provider can read: the provider can't fetch this host, so a site
		file is inlined as a data URL."""
		if self.data:
			return self.data
		if self.url.startswith("data:image/"):
			return self.url
		if self.url.startswith(("/files/", "/private/files/")):
			from builder.ai.agent.artifact import read_site_image

			return read_site_image(self.url)
		return None


class TurnImages:
	# Six images and the frames of one video, as the editor caps them.
	MAX_IMAGES = 14
	# A provider rejects an oversized request outright (Anthropic: 32 MB).
	MAX_TOTAL_BYTES = 20 * 1024 * 1024

	def __init__(self, images: list[AttachedImage] | None = None):
		self.images = images or []

	def __bool__(self) -> bool:
		return bool(self.images)

	def __len__(self) -> int:
		return len(self.images)

	@classmethod
	def from_request(cls, images: list | None) -> "TurnImages":
		images = [i for i in images or [] if isinstance(i, dict) and i.get("data")]
		if len(images) > cls.MAX_IMAGES:
			frappe.throw(_("Attach at most {0} images to a message.").format(cls.MAX_IMAGES))
		if sum(len(i["data"]) for i in images) > cls.MAX_TOTAL_BYTES:
			frappe.throw(_("These attachments are too large to send together. Remove some and try again."))
		for i in images:
			BlockCodec.validate_image_data(i["data"])
		# The address is the server's to assign once saved, never the client's.
		return cls([AttachedImage.from_dict({**i, "url": ""}) for i in images])

	@classmethod
	def from_payload(cls, images: list | None) -> "TurnImages":
		return cls([AttachedImage.from_dict(i) for i in images or []])

	@classmethod
	def from_metadata(cls, meta: dict) -> "TurnImages":
		if legacy := meta.get("attachedImageUrl"):
			return cls([AttachedImage(url=legacy)])
		return cls.from_payload(meta.get("attachedImages"))

	def save(self) -> None:
		for image in self.images:
			image.save()

	def metadata(self) -> list[dict]:
		return [image.to_dict() for image in self.images]

	def payload(self) -> list[dict]:
		return [image.to_dict(with_data=True) for image in self.images]

	def first(self, count: int) -> "TurnImages":
		return TurnImages(self.images[:count])

	def file_urls(self) -> set[str]:
		return {image.url for image in self.images if image.url.startswith("/")}

	def parts(self) -> list[dict]:
		"""Provider content parts, each image after a label naming it, so the model
		can tell video frames from separate images and refer to either by address."""
		parts = []
		for number, image in enumerate(self.images, 1):
			if url := image.inline_url():
				parts.append({"type": "text", "text": image.label(number)})
				parts.append({"type": "image_url", "image_url": {"url": url}})
		return parts

	def brief_note(self) -> str:
		"""The images ride as parts; a brief can only carry an image into the
		generation step by its address."""
		if not self.file_urls():
			return ""
		return (
			"\n\n(When an attached image should guide a build, carry its exact saved url in the "
			"brief on its own line: REFERENCE IMAGE: <url>)"
		)
