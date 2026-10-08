# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The installed files of an extension, served to its frames.

A frame runs at an opaque origin and sends no session, so this route serves
Guest. The code of an installed extension is public, like its GitHub release.

The URL holds the checksum of the build, so a file never changes under its URL
and the browser caches it for good. A rebuild gets new URLs. A URL with an old
checksum gets a 404, so a stale cache entry never gets new bytes.

These files come from extension authors, and they sit on the site's origin. A
user can open one in a tab. So every response is a sandboxed document: if a
file renders as a page, it runs at an opaque origin with no script.
"""

from pathlib import Path

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from builder.extensions.access import INSTALLATION_DOCTYPE
from builder.extensions.constants import ASSET_ROUTE, ASSET_TYPES

SECURITY_HEADERS = {
	# a frame at an opaque origin loads a module script only with a CORS header
	"Access-Control-Allow-Origin": "*",
	"X-Content-Type-Options": "nosniff",
	"Content-Security-Policy": "sandbox; default-src 'none'",
}

IMMUTABLE = "public, max-age=31536000, immutable"


class ExtensionAssetRenderer(BaseRenderer):
	"""Serves one installed file of an extension to a sandboxed frame."""

	def can_render(self) -> bool:
		return self.path.startswith(f"{ASSET_ROUTE}/")

	def render(self):
		file = self.get_file()
		if not file:
			return Response("Not found", status=404, headers=SECURITY_HEADERS, mimetype="text/plain")

		# the file descriptor stays open, and the middleware closes it
		stream = wrap_file(frappe.local.request.environ, file.open("rb"))
		headers = {**SECURITY_HEADERS, "Cache-Control": IMMUTABLE}
		return Response(stream, direct_passthrough=True, headers=headers, mimetype=ASSET_TYPES[file.suffix])

	def get_file(self) -> Path | None:
		"""The file this path names, if its installation is enabled and on this build."""
		parts = self.path.split("/", 3)
		if len(parts) != 4:
			return None

		_, name, checksum, relative_path = parts
		if not frappe.db.exists(INSTALLATION_DOCTYPE, name):
			return None

		installation = frappe.get_cached_doc(INSTALLATION_DOCTYPE, name)
		if not installation.enabled or installation.checksum != checksum:
			return None
		return installation.get_asset_path(relative_path)
