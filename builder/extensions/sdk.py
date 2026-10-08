# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Serves the one SDK build that all extension frames use.
A frame imports the SDK across origins. The web server sends no CORS header for
public files. So Builder serves the SDK itself."""

from functools import cached_property
from pathlib import Path

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from builder.extensions.assets import SECURITY_HEADERS
from builder.extensions.constants import ASSET_ROUTE

# `yarn build:sdk` writes this file. `builder_extension.html` imports it.
SDK_ROUTE = f"{ASSET_ROUTE}/sdk/extension-sdk.js"

# The URL does not change. So the browser checks the file each time, and gets 304 if it is the same.
CACHE_CONTROL = "public, no-cache"


class ExtensionSDKRenderer(BaseRenderer):
	"""Serves the extension SDK to a sandboxed frame."""

	def can_render(self) -> bool:
		return self.path == SDK_ROUTE

	def render(self):
		if frappe.local.request.headers.get("If-None-Match") == self.etag:
			return Response(status=304, headers=self.response_headers)

		# The middleware closes the file.
		stream = wrap_file(frappe.local.request.environ, open(self.file_path, "rb"))
		# The browser runs a module script only with the correct type.
		return Response(
			stream, direct_passthrough=True, headers=self.response_headers, mimetype="text/javascript"
		)

	@property
	def file_path(self) -> Path:
		return Path(frappe.get_app_path("builder", "public", "extension_sdk", "extension-sdk.js"))

	@cached_property
	def etag(self) -> str:
		stat = self.file_path.stat()
		return f'"{stat.st_mtime_ns}-{stat.st_size}"'

	@property
	def response_headers(self) -> dict:
		return {
			**SECURITY_HEADERS,
			"Cache-Control": CACHE_CONTROL,
			"ETag": self.etag,
		}
