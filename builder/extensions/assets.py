# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Serves the installed files of an extension to its frames.
A frame sends no session, so the route serves Guest. The URL has the build checksum.
So the browser keeps each file in its cache, and an old checksum gets 404."""

from pathlib import Path

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from builder.extensions.access import INSTALLATION_DOCTYPE
from builder.extensions.constants import ASSET_ROUTE, ASSET_TYPES

SECURITY_HEADERS = {
	# A frame loads a module script only with a CORS header.
	"Access-Control-Allow-Origin": "*",
	"X-Content-Type-Options": "nosniff",
	# A file that a user opens in a tab runs with no script.
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

		# The middleware closes the file.
		stream = wrap_file(frappe.local.request.environ, file.open("rb"))
		headers = {**SECURITY_HEADERS, "Cache-Control": IMMUTABLE}
		return Response(stream, direct_passthrough=True, headers=headers, mimetype=ASSET_TYPES[file.suffix])

	def get_file(self) -> Path | None:
		"""Returns the file for this path. Returns None if the installation is disabled or the build is old."""
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
