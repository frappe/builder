import json
import os
from io import BytesIO
from urllib.parse import unquote

import frappe
import requests
from frappe.apps import get_apps as get_permitted_apps
from frappe.core.doctype.file.file import get_local_image
from frappe.core.doctype.file.utils import delete_file
from frappe.integrations.utils import make_post_request
from frappe.model.document import Document
from frappe.utils.caching import redis_cache
from frappe.utils.telemetry import POSTHOG_HOST_FIELD, POSTHOG_PROJECT_FIELD
from PIL import Image

from builder.builder.doctype.builder_page.builder_page import BuilderPageRenderer


@frappe.whitelist()
def get_blocks(prompt):
	API_KEY = frappe.conf.openai_api_key
	if not API_KEY:
		frappe.throw("OpenAI API Key not set in site config.")

	messages = [
		{
			"role": "system",
			"content": "You are a website developer. You respond only with HTML code WITHOUT any EXPLANATION. You use any publicly available images in the webpage. You can use any font from fonts.google.com. Do not use any external css file or font files. DO NOT ADD <style> TAG AT ALL! You should use tailwindcss for styling the page. Use images from pixabay.com or unsplash.com",
		},
		{"role": "user", "content": prompt},
	]

	response = make_post_request(
		"https://api.openai.com/v1/chat/completions",
		headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
		data=json.dumps(
			{
				"model": "gpt-3.5-turbo",
				"messages": messages,
			}
		),
	)
	return response["choices"][0]["message"]["content"]


@frappe.whitelist()
def get_posthog_settings():
	can_record_session = False
	if start_time := frappe.db.get_default("session_recording_start"):
		time_difference = (
			frappe.utils.now_datetime() - frappe.utils.get_datetime(start_time)
		).total_seconds()
		if time_difference < 86400:  # 1 day
			can_record_session = True

	return {
		"posthog_project_id": frappe.conf.get(POSTHOG_PROJECT_FIELD),
		"posthog_host": frappe.conf.get(POSTHOG_HOST_FIELD),
		"enable_telemetry": frappe.get_system_settings("enable_telemetry"),
		"telemetry_site_age": frappe.utils.telemetry.site_age(),
		"record_session": can_record_session,
		"posthog_identifier": frappe.local.site,
	}


@frappe.whitelist()
def get_page_preview_html(page: str, **kwarg) -> str:
	# to load preview without publishing
	frappe.form_dict.update(kwarg)
	renderer = BuilderPageRenderer(path="")
	renderer.docname = page
	renderer.doctype = "Builder Page"
	frappe.flags.show_preview = True
	frappe.local.no_cache = 1
	renderer.init_context()
	response = renderer.render()
	page = frappe.get_cached_doc("Builder Page", page)
	frappe.enqueue_doc(
		page.doctype,
		page.name,
		"generate_page_preview_image",
		html=str(response.data, "utf-8"),
		queue="short",
	)
	return response


@frappe.whitelist()
def upload_builder_asset():
	from frappe.handler import upload_file

	image_file = upload_file()
	if image_file.file_url.endswith((".png", ".jpeg", ".jpg")) and frappe.get_cached_value(
		"Builder Settings", None, "auto_convert_images_to_webp"
	):
		convert_to_webp(file_doc=image_file)
	return image_file


@frappe.whitelist()
def convert_to_webp(image_url: str | None = None, file_doc: Document | None = None) -> str:
	"""BETA: Convert image to webp format"""

	CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

	def can_convert_image(extn):
		return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

	def get_extension(filename):
		return filename.split(".")[-1].lower()

	def convert_and_save_image(image, path):
		image.save(path, "WEBP")
		return path

	def update_file_doc_with_webp(file_doc, image, extn):
		webp_path = file_doc.get_full_path().replace(extn, "webp")
		convert_and_save_image(image, webp_path)
		delete_file(file_doc.get_full_path())
		file_doc.file_url = f"{file_doc.file_url.replace(extn, 'webp')}"
		file_doc.save()
		return file_doc.file_url

	def create_new_webp_file_doc(file_url, image, extn):
		files = frappe.get_all("File", filters={"file_url": file_url}, fields=["name"], limit=1)
		if files:
			_file = frappe.get_doc("File", files[0].name)
			webp_path = _file.get_full_path().replace(extn, "webp")
			convert_and_save_image(image, webp_path)
			new_file = frappe.copy_doc(_file)
			new_file.file_name = f"{_file.file_name.replace(extn, 'webp')}"
			new_file.file_url = f"{_file.file_url.replace(extn, 'webp')}"
			new_file.save()
			return new_file.file_url
		return file_url

	def handle_image_from_url(image_url):
		image_url = unquote(image_url)
		response = requests.get(image_url)
		image = Image.open(BytesIO(response.content))
		filename = image_url.split("/")[-1]
		extn = get_extension(filename)
		if can_convert_image(extn):
			_file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"{filename.replace(extn, 'webp')}",
					"file_url": f"/files/{filename.replace(extn, 'webp')}",
				}
			)
			webp_path = _file.get_full_path()
			convert_and_save_image(image, webp_path)
			_file.save()
			return _file.file_url
		return image_url

	if not image_url and not file_doc:
		return ""

	if file_doc:
		if file_doc.file_url.startswith("/files"):
			image, filename, extn = get_local_image(file_doc.file_url)
			if can_convert_image(extn):
				return update_file_doc_with_webp(file_doc, image, extn)
		return file_doc.file_url

	if image_url.startswith("/files"):
		image, filename, extn = get_local_image(image_url)
		if can_convert_image(extn):
			return create_new_webp_file_doc(image_url, image, extn)
		return image_url

	if image_url.startswith("/builder_assets"):
		image_path = os.path.abspath(frappe.get_app_path("builder", "www", image_url.lstrip("/")))
		image_path = image_path.replace("_", "-")
		image_path = image_path.replace("/builder-assets", "/builder_assets")

		image = Image.open(image_path)
		extn = get_extension(image_path)
		if can_convert_image(extn):
			webp_path = image_path.replace(extn, "webp")
			convert_and_save_image(image, webp_path)
			return image_url.replace(extn, "webp")
		return image_url

	if image_url.startswith("http"):
		return handle_image_from_url(image_url)

	return image_url


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	if frappe.has_permission("Builder Page", ptype="write"):
		return True

	return False


@frappe.whitelist()
@redis_cache()
def get_apps():
	apps = get_permitted_apps()
	app_list = [
		{
			"name": "frappe",
			"logo": "/assets/builder/images/desk.png",
			"title": "Desk",
			"route": "/app",
		}
	]
	app_list += filter(lambda app: app.get("name") != "builder", apps)

	return app_list
