# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The one SDK build every extension frame shares.

The frame's import map resolves the bare `frappe-builder-extension-sdk`
specifier to this URL, and a module script at an opaque origin is a cross-origin
request. The web server sends no CORS header for the app's public directory, so
Builder answers this one itself. `assets.py` serves the extensions' own files.
"""

from functools import cached_property
from pathlib import Path

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from builder.extensions.assets import SECURITY_HEADERS
from builder.extensions.constants import ASSET_ROUTE

# `yarn build:sdk` writes this one file, and `builder_extension.html` imports it
SDK_ROUTE = f"{ASSET_ROUTE}/sdk/extension-sdk.js"

# The name never changes, so the file cannot be immutable. It revalidates, and an
# unchanged build answers 304.
CACHE_CONTROL = "public, no-cache"


class ExtensionSDKRenderer(BaseRenderer):
	"""Serves the extension SDK to a sandboxed frame."""

	def can_render(self) -> bool:
		return self.path == SDK_ROUTE

	def render(self):
		if frappe.local.request.headers.get("If-None-Match") == self.etag:
			return Response(status=304, headers=self.response_headers)

		# the file descriptor stays open, and the middleware closes it
		stream = wrap_file(frappe.local.request.environ, open(self.file_path, "rb"))
		# a module script is MIME-strict: the wrong type stops the browser running it
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
