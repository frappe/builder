import base64
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

	def is_external_image(image_url):
		return image_url.startswith("http") or image_url.startswith("https")

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
		if can_convert_image(extn) or is_external_image(image_url):
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


@frappe.whitelist()
def update_page_folder(pages: list[str], folder_name: str) -> None:
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to update page folder.")
	for page in pages:
		frappe.db.set_value("Builder Page", page, "project_folder", folder_name, update_modified=False)


@frappe.whitelist()
def duplicate_page(page_name: str):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to duplicate a page.")
	page = frappe.get_doc("Builder Page", page_name)
	new_page = frappe.copy_doc(page)
	del new_page.page_name
	new_page.route = None
	client_scripts = page.client_scripts
	new_page.client_scripts = []
	for script in client_scripts:
		builder_script = frappe.get_doc("Builder Client Script", script.builder_script)
		new_script = frappe.copy_doc(builder_script)
		new_script.name = f"{builder_script.name}-{frappe.generate_hash(length=5)}"
		new_script.insert(ignore_permissions=True)
		new_page.append("client_scripts", {"builder_script": new_script.name})
	new_page.insert()
	return new_page


@frappe.whitelist()
def delete_folder(folder_name: str) -> None:
	if not frappe.has_permission("Builder Project Folder", ptype="write"):
		frappe.throw("You do not have permission to delete a folder.")

	# remove folder from all pages
	pages = frappe.get_all("Builder Page", filters={"project_folder": folder_name}, fields=["name"])
	for page in pages:
		frappe.db.set_value("Builder Page", page.name, "project_folder", "", update_modified=False)

	frappe.db.delete("Builder Project Folder", folder_name)


@frappe.whitelist()
def sync_component(component_id: str):
	if not frappe.has_permission("Builder Page", ptype="write"):
		frappe.throw("You do not have permission to sync a component.")

	component = frappe.get_doc("Builder Component", component_id)
	component.sync_component()


@frappe.whitelist()
def get_page_analytics(route=None, date_range: str = "last_30_days", interval=None):
	"""Get analytics data for a specific page route or all pages."""
	try:
		if not route and not frappe.has_permission("Web Page View", "read"):
			return _get_empty_analytics()

		date_config = _get_date_config(date_range)
		if not date_config:
			return _get_empty_analytics()

		to_date = frappe.utils.now_datetime()
		from_date = _calculate_from_date(to_date, date_config)
		interval = interval or date_config["default_interval"]

		views_data = _get_page_views(route, from_date)
		grouped_data = _group_analytics_data(views_data, from_date, to_date, interval)

		return {
			"total_unique_views": sum(frappe.utils.cint(d.get("is_unique", 0)) for d in views_data),
			"total_views": len(views_data),
			"data": grouped_data,
		}
	except Exception as e:
		frappe.log_error("Analytics Error", str(e))
		return _get_empty_analytics()


def _get_empty_analytics():
	return {"total_unique_views": 0, "total_views": 0, "data": []}


def _get_date_config(date_range):
	return {
		"today": {"delta": -24, "unit": "hours", "default_interval": "hourly"},
		"this_week": {"delta": -7, "unit": "days", "default_interval": "daily"},
		"last_7_days": {"delta": -7, "unit": "days", "default_interval": "daily"},
		"last_30_days": {"delta": -30, "unit": "days", "default_interval": "daily"},
		"last_90_days": {"delta": -90, "unit": "days", "default_interval": "weekly"},
		"last_180_days": {"delta": -180, "unit": "days", "default_interval": "weekly"},
		"this_year": {"delta": None, "unit": None, "default_interval": "monthly"},
	}.get(date_range)


def _calculate_from_date(to_date, config):
	if config["delta"] is None:  # Handle "this_year" case
		return frappe.utils.get_datetime(f"{to_date.year}-01-01")
	return frappe.utils.add_to_date(to_date, **{config["unit"]: config["delta"]})


def _get_page_views(route, from_date):
	filters = {
		"creation": [">=", from_date],
	}
	if route:
		filters["path"] = route

	return frappe.get_all(
		"Web Page View",
		filters=filters,
		fields=["creation", "is_unique", "path"],
	)


def _group_analytics_data(views_data, from_date, to_date, interval):
	formats = {
		"hourly": "%I %p",  # 01 PM
		"daily": "%d %b",  # 25 Jan
		"weekly": "%d %b, Week %W",  # Week of Jan
		"monthly": "%b %Y",  # Jan 2024
	}

	interval_deltas = {
		"hourly": {"hours": 1},
		"daily": {"days": 1},
		"weekly": {"days": 7},
		"monthly": {"months": 1},
	}

	fmt = formats[interval]
	delta = interval_deltas[interval]

	# Initialize all dates in range with zero counts
	grouped_data = {}
	current_date = from_date
	while current_date <= to_date:
		key = current_date.strftime(fmt)
		grouped_data[key] = {"total_page_views": 0, "unique_page_views": 0, "timestamp": current_date}
		current_date = frappe.utils.add_to_date(current_date, **delta)

	# Fill in actual data where it exists
	for view in views_data:
		key = view.creation.strftime(fmt)
		if key in grouped_data:
			grouped_data[key]["total_page_views"] += 1
			grouped_data[key]["unique_page_views"] += frappe.utils.cint(view.is_unique)

	sorted_data = sorted(grouped_data.items(), key=lambda x: x[1]["timestamp"])
	return [
		{
			"interval": k,
			"total_page_views": v["total_page_views"],
			"unique_page_views": v["unique_page_views"],
		}
		for k, v in sorted_data
	]


def _get_top_referrers(date_range: str = "last_30_days"):
	from urllib.parse import urlparse

	date_config = _get_date_config(date_range)
	from_date = _calculate_from_date(frappe.utils.now_datetime(), date_config)
	WebPageView = frappe.qb.DocType("Web Page View")
	# Get all referrers in the date range
	referrers = (
		frappe.qb.from_(WebPageView)
		.select(WebPageView.referrer)
		.where(WebPageView.creation >= from_date)
		.run(as_dict=True)
	)
	# Count by domain
	domain_counts = {}
	for row in referrers:
		ref = row.get("referrer")
		if not ref:
			continue
		try:
			domain = urlparse(ref).netloc.lower()
			if domain:
				domain_counts[domain] = domain_counts.get(domain, 0) + 1
		except Exception:
			continue
	# Sort and return top 20
	top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:20]
	return [{"domain": d, "count": c} for d, c in top_domains]


@frappe.whitelist()
def get_overall_analytics(date_range: str = "last_30_days", interval=None):
	"""Get overall site analytics with top pages and top referrers."""
	analytics = get_page_analytics(None, date_range, interval)
	analytics["top_pages"] = _get_top_pages(date_range=date_range)
	analytics["top_referrers"] = _get_top_referrers(date_range=date_range)
	return analytics


def _get_top_pages(date_range: str = "last_30_days"):
	from frappe.query_builder.functions import Count, Sum

	date_config = _get_date_config(date_range)
	from_date = _calculate_from_date(frappe.utils.now_datetime(), date_config)
	WebPageView = frappe.qb.DocType("Web Page View")
	pages = (
		frappe.qb.from_(WebPageView)
		.select(
			WebPageView.path.as_("route"),
			Count(WebPageView.path).as_("view_count"),
			Sum(frappe.qb.terms.Case().when(WebPageView.is_unique == "1", 1).else_(0)).as_(
				"unique_view_count"
			),
		)
		.where(WebPageView.creation >= from_date)
		.groupby(WebPageView.path)
		.orderby("view_count", order=frappe.qb.desc)
		.limit(20)
		.run(as_dict=True)
	)
	return pages
