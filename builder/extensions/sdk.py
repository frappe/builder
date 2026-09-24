# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The one SDK build every extension frame shares.

Nothing else is served here. An extension's own code reaches its frame through
the connect handshake, because a frame sends no session and no route could tell
one user's request from another's.

The frame still needs this file over HTTP: its import map resolves the bare
`frappe-builder-extension-sdk` specifier to this URL, and a module script at an
opaque origin is a cross-origin request. The web server sends no CORS header for
the app's public directory, so Builder answers this one itself.
"""

from functools import cached_property
from pathlib import Path

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

# `yarn build:sdk` writes this one file, and `builder_extension.html` imports it
SDK_ROUTE = "builder_extension_asset/sdk/extension-sdk.js"

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
			"Access-Control-Allow-Origin": "*",
			"Cache-Control": CACHE_CONTROL,
			"ETag": self.etag,
		}
