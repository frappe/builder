import ipaddress
import os
import socket
from io import BytesIO
from types import FunctionType, MethodType, ModuleType
from typing import Any
from urllib.parse import unquote, urlparse

import frappe
import requests
from frappe.apps import get_apps as get_permitted_apps
from frappe.core.doctype.file.file import get_local_image
from frappe.core.doctype.file.utils import delete_file
from frappe.model.document import Document
from frappe.utils.caching import redis_cache
from frappe.utils.safe_exec import NamespaceDict, get_safe_globals
from PIL import Image
from werkzeug.wrappers import Response

from builder import builder_analytics
from builder.builder.doctype.builder_page.builder_page import BuilderPageRenderer
from builder.utils import has_page_read, has_page_write


@frappe.whitelist()
def get_page_preview_html(page: str, **kwarg) -> Response:
	if not frappe.has_permission("Builder Page", "read", page):
		frappe.throw("No permission to preview this page")

	# to load preview without publishing
	frappe.form_dict.update(kwarg)
	frappe.local.request.for_preview = True
	renderer = BuilderPageRenderer(path="")
	renderer.docname = page
	renderer.doctype = "Builder Page"
	frappe.local.no_cache = 1
	renderer.init_context()
	response = renderer.render()
	page_doc = frappe.get_cached_doc("Builder Page", page)
	frappe.enqueue_doc(
		page_doc.doctype,
		page_doc.name,
		"generate_page_preview_image",
		html=str(response.data, "utf-8"),
		queue="short",
	)
	return response


@frappe.whitelist()
@has_page_write("You do not have permission to upload assets.")
def upload_builder_asset():
	from frappe.handler import upload_file

	image_file = upload_file()
	if image_file.file_url.endswith((".png", ".jpeg", ".jpg")) and frappe.get_cached_value(
		"Builder Settings", "Builder Settings", "auto_convert_images_to_webp"
	):
		convert_to_webp(file_doc=image_file)
	return image_file


@frappe.whitelist()
def convert_to_webp(image_url: str | None = None, file_doc: Document | None = None) -> str:
	"""
	Convert image to webp format.
	Handles local files, builder assets, and external URLs.
	Returns the new webp file URL or the original if conversion is not possible.
	"""
	import hashlib

	CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

	def can_convert_image(extn: str) -> bool:
		return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

	def get_extension(filename: str) -> str:
		return filename.split(".")[-1].lower() if "." in filename else ""

	def save_as_webp(image, path: str) -> None:
		image.save(path, "WEBP")

	def to_webp_url(url: str, extn: str) -> str:
		return url.replace(extn, "webp")

	def to_webp_path(path: str, extn: str) -> str:
		return path.replace(extn, "webp")

	def handle_file_doc(file_doc: Document) -> str:
		if not file_doc.file_url.startswith("/files"):
			return file_doc.file_url
		image, _, extn = get_local_image(file_doc.file_url)
		if not can_convert_image(extn):
			return file_doc.file_url
		save_as_webp(image, to_webp_path(file_doc.get_full_path(), extn))
		delete_file(file_doc.get_full_path())
		file_doc.file_url = to_webp_url(file_doc.file_url, extn)
		file_doc.save()
		return file_doc.file_url

	def handle_local_url(image_url: str) -> str:
		image, _, extn = get_local_image(image_url)
		if not can_convert_image(extn):
			return image_url
		files = frappe.get_all("File", filters={"file_url": image_url}, fields=["name"], limit=1)
		if not files:
			return image_url
		file = frappe.get_doc("File", files[0].name)
		save_as_webp(image, to_webp_path(file.get_full_path(), extn))
		new_file = frappe.copy_doc(file)
		new_file.file_name = to_webp_url(file.file_name, extn)
		new_file.file_url = to_webp_url(file.file_url, extn)
		new_file.save()
		return new_file.file_url

	def handle_builder_asset(image_url: str) -> str:
		image_path = os.path.abspath(frappe.get_app_path("builder", "www", image_url.lstrip("/")))
		image_path = image_path.replace("_", "-").replace("/builder-assets", "/builder_assets")
		extn = get_extension(image_path)
		if not can_convert_image(extn):
			return image_url
		image = Image.open(image_path)
		save_as_webp(image, to_webp_path(image_path, extn))
		return to_webp_url(image_url, extn)

	def get_external_webp_filename(image_url: str) -> str:
		filename = image_url.split("/")[-1].split("?")[0]
		base = filename.rsplit(".", 1)[0] if "." in filename else ""
		if not base or base.lower() == "webp" or filename.lower() == "webp":
			return f"external-{hashlib.md5(image_url.encode()).hexdigest()[:8]}.webp"
		return base + ".webp"

	def handle_external_url(image_url: str) -> str:
		url = unquote(image_url)
		assert_not_private_url(url)
		image = Image.open(BytesIO(requests.get(url).content))
		filename = get_external_webp_filename(url)
		file = frappe.get_doc({"doctype": "File", "file_name": filename, "file_url": f"/files/{filename}"})
		save_as_webp(image, file.get_full_path())
		file.save()
		return file.file_url

	if not image_url and not file_doc:
		return ""
	if file_doc:
		return handle_file_doc(file_doc)

	image_url = image_url or ""
	if image_url.startswith("/files"):
		return handle_local_url(image_url)
	if image_url.startswith("/builder_assets"):
		return handle_builder_asset(image_url)
	if image_url.startswith("http"):
		return handle_external_url(image_url)
	return image_url


def assert_not_private_url(url: str) -> None:
	"""Raise PermissionError if the URL resolves to a private/internal IP (SSRF guard)."""
	parsed = urlparse(url)
	if parsed.scheme not in ("http", "https"):
		frappe.throw("Only HTTP/HTTPS URLs are allowed for external images.", frappe.PermissionError)
	hostname = parsed.hostname
	if not hostname:
		frappe.throw("Invalid URL: missing hostname.", frappe.ValidationError)
	try:
		addr_infos = socket.getaddrinfo(hostname, None)
	except socket.gaierror:
		frappe.throw(f"Could not resolve hostname: {hostname}", frappe.ValidationError)
	for addr_info in addr_infos:
		ip = ipaddress.ip_address(addr_info[4][0])
		if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
			frappe.throw("Requests to private or internal addresses are not allowed.", frappe.PermissionError)


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
@has_page_write("You do not have permission to update page folder.")
def update_page_folder(pages: list[str], folder_name: str) -> None:
	if not pages:
		return
	frappe.db.set_value(
		"Builder Page", {"name": ["in", pages]}, "project_folder", folder_name, update_modified=False
	)


def clone_client_scripts(source_page, new_page) -> None:
	"""Clone the source page's client scripts onto new_page with hashed names,
	so the copy never shares scripts with the source."""
	client_scripts = source_page.client_scripts
	new_page.client_scripts = []
	for script in client_scripts:
		builder_script = frappe.get_doc("Builder Client Script", script.builder_script)
		new_script = frappe.copy_doc(builder_script)
		new_script.name = f"{builder_script.name}-{frappe.generate_hash(length=5)}"
		new_script.insert(ignore_permissions=True)
		new_page.append("client_scripts", {"builder_script": new_script.name})


@frappe.whitelist()
@has_page_write("You do not have permission to duplicate a page.")
def duplicate_page(page_name: str):
	page = frappe.get_doc("Builder Page", page_name)
	new_page = frappe.copy_doc(page)
	del new_page.page_name
	new_page.route = None
	clone_client_scripts(page, new_page)
	new_page.insert()
	return new_page


# Templates are served by a central Builder Hub site; a builder site fetches the
# catalog + a per-page bundle over HTTP (server-side proxy — no CORS needed) and
# materializes a page locally on demand. Override the hub via Builder Settings >
# Template Hub URL, or site_config template_hub_url.
#
# NOTE: this default is a PLACEHOLDER for the eventual production hub and does not
# resolve yet. Until that hub is deployed (or this constant is updated), a site
# must set `template_hub_url` to get templates; otherwise the catalog fetch fails
# gracefully and the picker shows only "Blank page" + the user's own My Templates.
DEFAULT_HUB_URL = "https://builder-hub.frappe.cloud"
MY_TEMPLATES = "__my_templates__"


def _hub_url() -> str:
	url = (
		frappe.get_cached_value("Builder Settings", "Builder Settings", "template_hub_url")
		or frappe.conf.get("template_hub_url")
		or DEFAULT_HUB_URL
	)
	return url.rstrip("/")


def _abs_url(path: str | None) -> str | None:
	"""Absoluteize a site-relative (/...) url; leave absolute/None urls as-is."""
	if path and isinstance(path, str) and path.startswith("/"):
		return frappe.utils.get_url() + path
	return path


def build_template_catalog(
	app: str = "builder", template_group: str | None = None, absolute_preview: bool = False
) -> list[dict]:
	"""Build the template-group catalog from local DB template pages + on-disk
	manifests. Shared by builder (local "My Templates") and the hub (public catalog).

	template_group:
	  None         -> manifest-backed groups only (the hub's public catalog)
	  MY_TEMPLATES -> only ungrouped user-saved templates, as one "My Templates" group
	absolute_preview: prefix preview + add per-page live_url with this site's URL
	  (so a remote consumer can load images / open Preview against the hub).
	"""
	from builder.template_sync import get_all_group_manifests

	fields = ["name", "page_title", "preview", "route", "template_group"]

	def decorate(pages):
		if absolute_preview:
			for p in pages:
				p.preview = _abs_url(p.preview)
				p.live_url = _abs_url(f"/{p.route}") if p.route else None
		return pages

	if template_group == MY_TEMPLATES:
		pages = decorate(
			frappe.get_all(
				"Builder Page",
				filters={"is_template": 1, "template_group": ("is", "not set")},
				fields=fields,
				order_by="creation asc",
				ignore_permissions=True,
			)
		)
		if not pages:
			return []
		return [
			{
				"name": "my_templates",
				"title": "My Templates",
				"description": "Pages you saved as templates",
				"preview": pages[0].preview,
				"pages": pages,
			}
		]

	pages = decorate(
		frappe.get_all(
			"Builder Page",
			filters={"is_template": 1, "template_group": ("is", "set")},
			fields=fields,
			order_by="creation asc",
			ignore_permissions=True,
		)
	)
	pages_by_group: dict[str, list] = {}
	for page in pages:
		pages_by_group.setdefault(page.template_group, []).append(page)

	groups = []
	for group, manifest in get_all_group_manifests(app).items():
		group_pages = pages_by_group.pop(group, [])
		if not group_pages:
			continue
		manifest_order = {
			page.get("name"): idx
			for idx, page in enumerate(manifest.get("pages") or [])
			if isinstance(page, dict)
		}
		group_pages.sort(key=lambda p: (manifest_order.get(p.name, len(manifest_order)), p.page_title or ""))
		preview = _abs_url(manifest.get("preview")) if absolute_preview else manifest.get("preview")
		groups.append(
			{
				"name": group,
				"title": manifest.get("title") or group.replace("_", " ").title(),
				"description": manifest.get("description") or "",
				"preview": preview or group_pages[0].preview,
				"order": manifest.get("order"),
				"pages": group_pages,
			}
		)
	# grouped pages whose manifest is missing on disk should still show up
	for group, group_pages in pages_by_group.items():
		groups.append(
			{
				"name": group,
				"title": group.replace("_", " ").title(),
				"description": "",
				"preview": group_pages[0].preview,
				"pages": group_pages,
			}
		)
	groups.sort(key=lambda g: (g.get("order") is None, g.get("order") or 0, g["title"]))
	return groups


@redis_cache(ttl=600)
def _fetch_hub_catalog() -> list[dict]:
	"""Fetch the remote hub catalog (grouped templates). Cached; empty on failure
	so the picker degrades to Blank + local My Templates when the hub is down."""
	from frappe.integrations.utils import make_get_request

	try:
		# NOTE: make_get_request (not builder's make_safe_get_request, which blocks
		# private IPs and would reject a localhost hub). Trust = admin-set hub URL.
		resp = make_get_request(f"{_hub_url()}/api/method/builder_hub.api.get_catalog")
		return resp.get("message") or []
	except Exception:
		frappe.log_error("Failed to fetch template hub catalog")
		return []


@frappe.whitelist()
@has_page_read("You do not have permission to view templates.")
def get_template_groups() -> list[dict]:
	"""Catalog for the template picker: remote hub groups (cached) + the user's
	own locally-saved "My Templates" (live)."""
	groups = list(_fetch_hub_catalog())
	groups += build_template_catalog(app="builder", template_group=MY_TEMPLATES)
	return groups


@frappe.whitelist()
@has_page_write("You do not have permission to create a page.")
def create_page_from_template(template_page: str, project_folder: str | None = None) -> str:
	"""Create an editable page from a template and return its name.

	`template_page` is either a local "My Template" page name or a hub page id.
	Created pages hot-link the hub's /builder_assets/ images (known v1 gap — a
	live page depends on hub availability; future: copy assets local on create)."""
	if frappe.db.exists("Builder Page", template_page):
		tpl = frappe.db.get_value(
			"Builder Page", template_page, ["is_template", "template_group"], as_dict=True
		)
		if tpl and tpl.is_template and not tpl.template_group:
			return _create_from_local_template(template_page, project_folder)
	return _create_from_hub_template(template_page, project_folder)


def _create_from_local_template(template_page: str, project_folder: str | None) -> str:
	template = frappe.get_doc("Builder Page", template_page)
	if not template.is_template:
		frappe.throw(f"{template_page} is not a template page")
	new_page = frappe.copy_doc(template)
	new_page.is_template = 0
	new_page.template_group = None
	del new_page.page_name
	new_page.route = None
	new_page.published = 0
	new_page.published_at = None
	new_page.draft_blocks = template.draft_blocks or template.blocks  # opens as draft
	new_page.blocks = None
	if project_folder:
		new_page.project_folder = project_folder
	clone_client_scripts(template, new_page)
	new_page.insert()
	return new_page.name


def _create_from_hub_template(template_page: str, project_folder: str | None) -> str:
	from frappe.integrations.utils import make_get_request
	from frappe.modules.import_file import import_doc

	try:
		resp = make_get_request(
			f"{_hub_url()}/api/method/builder_hub.api.get_template_bundle",
			params={"page": template_page},
		)
		bundle = resp.get("message")
	except Exception:
		frappe.log_error("Failed to fetch template bundle")
		bundle = None
	if not bundle or not bundle.get("page"):
		frappe.throw(frappe._("Could not load the selected template. Please try again."))

	# install shared deps (stable names → var(--uuid)/extendedFromComponent resolve);
	# the read-only guard is inert here (import sets frappe.flags.in_import)
	for font in bundle.get("fonts") or []:
		import_doc(docdict=font)
	for var in bundle.get("variables") or []:
		import_doc(docdict=var)
	for comp in bundle.get("components") or []:
		import_doc(docdict=comp)

	page = bundle["page"]
	new_page = frappe.get_doc(
		{
			"doctype": "Builder Page",
			"is_template": 0,
			"template_group": None,
			"page_title": page.get("page_title") or "My Page",
			"draft_blocks": frappe.as_json(page.get("blocks") or []),  # opens as draft
			"page_data_script": page.get("page_data_script"),
			"head_html": page.get("head_html"),
			"body_html": page.get("body_html"),
			"meta_description": page.get("meta_description"),
			"published": 0,
		}
	)
	if project_folder:
		new_page.project_folder = project_folder
	# fresh client scripts from the bundle (hashed names) — never reuse hub names
	for cs in bundle.get("client_scripts") or []:
		new_script = frappe.get_doc(
			{
				"doctype": "Builder Client Script",
				"name": f"{cs.get('name')}-{frappe.generate_hash(length=5)}",
				"script_type": cs.get("script_type"),
				"script": cs.get("script"),
			}
		)
		new_script.insert(ignore_permissions=True)
		new_page.append("client_scripts", {"builder_script": new_script.name})
	new_page.insert()
	return new_page.name


@frappe.whitelist()
@has_page_write("You do not have permission to delete a folder.")
def delete_folder(folder_name: str) -> None:
	# remove folder from all pages in a single update
	frappe.db.set_value(
		"Builder Page", {"project_folder": folder_name}, "project_folder", "", update_modified=False
	)

	frappe.db.delete("Builder Project Folder", {"folder_name": folder_name})


@frappe.whitelist()
@has_page_write("You do not have permission to sync a component.")
def sync_component(component_id: str):
	component = frappe.get_doc("Builder Component", component_id)
	component.sync_component()


@frappe.whitelist()
@has_page_read("You do not have permission to view analytics.")
def get_page_analytics(
	route: str,
	interval: str = "daily",
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	return builder_analytics.get_page_analytics(
		route=route,
		interval=interval,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


@frappe.whitelist()
@has_page_read("You do not have permission to view analytics.")
def get_overall_analytics(
	interval: str = "daily",
	route: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	return builder_analytics.get_overall_analytics(
		interval=interval,
		route=route,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)


def get_keys_for_autocomplete(
	key: str,
	value: Any,
	depth: int = 0,
	max_depth: int | None = None,
):
	if max_depth and depth > max_depth:
		return None  # Or some other sentinel value to indicate termination

	if key.startswith("_"):
		return None

	if isinstance(value, NamespaceDict | dict) and value:
		result = {}
		for k, v in value.items():
			nested_result = get_keys_for_autocomplete(
				k,
				v,
				depth + 1,
				max_depth=max_depth,
			)
			if nested_result is not None:  # Only add if not terminated
				result[k] = nested_result
		return result if result else None  # Return None if the dictionary is empty

	else:
		if isinstance(value, type) and issubclass(value, Exception):
			var_type = "type"  # Exceptions are types
		elif isinstance(value, ModuleType):
			var_type = "namespace"
		elif isinstance(value, FunctionType | MethodType):
			var_type = "function"
		elif isinstance(value, type):
			var_type = "type"
		elif isinstance(value, dict):
			var_type = "property"  # Assuming dict should be mapped to other
		else:
			var_type = "property"  # Default to text if no other type matches
		return {"true_type": type(value).__name__, "type": var_type}


@frappe.whitelist()
@redis_cache()
def get_codemirror_completions():
	return get_keys_for_autocomplete(
		key="",
		value=get_safe_globals(),
	)


@frappe.whitelist()
@has_page_write("You do not have permission to reorder client scripts")
def reorder_client_scripts(script_order: list[str]):
	for idx, script_name in enumerate(script_order, start=1):
		frappe.db.set_value("Builder Page Client Script", script_name, "idx", idx)
