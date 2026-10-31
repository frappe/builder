"""Photos the user uploads through a card reach Bob as /files/ urls in their reply text.
Bob looks at them before designing: each is attached to the turn as an image with its
size, so the design starts from what the material shows and how large it can go."""

import base64
import io
import os
import re
from urllib.parse import unquote

import frappe

FILE_URL = re.compile(r"(/(?:private/)?files/[^\n,;:]+?\.(?:png|jpe?g|webp|gif))", re.I)
MAX_UPLOADS = 6
VIEW_EDGE = 1024


def find(texts: list[str]) -> list[str]:
	"""Site image urls in the texts, oldest first, without repeats; the newest few."""
	seen: list[str] = []
	for text in texts:
		for url in FILE_URL.findall(text or ""):
			if url not in seen:
				seen.append(url)
	return seen[-MAX_UPLOADS:]


def attach(urls: list[str]) -> tuple[str, list[dict]]:
	"""A note naming each readable upload with its size, and the image parts that show them."""
	lines, parts = [], []
	for url in urls:
		if (image := load(url)) is None:
			continue
		lines.append(f"- {url}: {image.width}x{image.height}px")
		parts.append({"type": "image_url", "image_url": {"url": data_url(image)}})
	if not parts:
		return "", []
	note = (
		"Photos the user uploaded in this conversation, attached below in this order. Look at what "
		"each shows and how large it can go before you design:\n" + "\n".join(lines)
	)
	return note, parts


def load(url: str):
	from PIL import Image

	path = unquote(url).lstrip("/")
	if path.startswith("private/") and not can_read(unquote(url)):
		return None
	full = frappe.get_site_path(path) if path.startswith("private/") else frappe.get_site_path("public", path)
	if not os.path.isfile(full):
		return None
	try:
		return Image.open(full)
	except Exception:
		return None


def can_read(url: str) -> bool:
	name = frappe.db.get_value("File", {"file_url": url}, "name")
	return bool(name) and frappe.get_doc("File", name).has_permission("read")


def data_url(image) -> str:
	image = image.convert("RGB")
	image.thumbnail((VIEW_EDGE, VIEW_EDGE))
	buffer = io.BytesIO()
	image.save(buffer, "WEBP", quality=80)
	return "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode()
