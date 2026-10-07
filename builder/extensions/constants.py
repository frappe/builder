# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What an extension may be named, hold, and ask for.

Its own module, so the extension modules and the DocTypes share it without
importing each other.
"""

import re

EXTENSIONS_FOLDER = "extensions"
MANIFEST_FILE = "manifest.json"
ENTRY_FILE = "main.js"

# The route that serves the SDK and the installed files to extension frames
ASSET_ROUTE = "builder_extension_asset"

# The files a frame may load, by suffix. No HTML or XML: a tab that opens one of
# these URLs must not get a page that runs as the site
ASSET_TYPES = {
	".js": "text/javascript",
	".css": "text/css",
	".json": "application/json",
	".svg": "image/svg+xml",
	".png": "image/png",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".gif": "image/gif",
	".webp": "image/webp",
	".woff": "font/woff",
	".woff2": "font/woff2",
}

# publisher/name, lowercase. The slash is the only separator, and no install path
# is built from it, so a name can add no path segment.
EXTENSION_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")

# One SVG in the install root. No separator, so an icon names no file outside it.
# No other format, so the editor draws it in an <img> at any size.
ICON_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.svg$")

# every permission the bridge gates a method by. Reads and windows need none
PERMISSIONS = (
	"page.edit",
	"page.write",
	"token.write",
	"data.access",
	"schema.write",
	"method.call",
)

# An installation loaded from a dev server this session. It has no files, and the
# browser adds its own entry for it, so the listing leaves it out.
DEV_EXTENSION_VERSION = "0.0.0-dev"

# A README is prose, and the panel renders it in a 300 pixel column. This is room
# for a long one and no room for a book.
MAX_README_BYTES = 100_000

# Room for settings and a cached list. Small enough that no extension fills a
# site with what it remembers.
MAX_STATE_BYTES = 100_000

# The largest file a package may hold. It matches the Hub.
MAX_FILE_BYTES = 5 * 1024 * 1024

# The Builder Hub a site reads its catalog from when no other URL is set. It must
# match the default on `Builder Settings.hub_url`.
DEFAULT_HUB_URL = "https://preview.frappe.cloud"

# The extension protocol this Builder speaks. A release that needs a newer one is
# refused, and the Hub is asked for a release at or below this.
PROTOCOL_VERSION = 1

# A `.builderext` package is one ZIP: the manifest, `main.js` and the icon at the
# root, and the build's `chunks/` and `assets/`. These bound what Builder will
# download and unpack from it. They match the Hub.
PACKAGE_FOLDERS = frozenset({"chunks", "assets"})
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_BYTES = 30 * 1024 * 1024
MAX_PACKAGE_FILES = 200
MAX_MANIFEST_BYTES = 128 * 1024
MAX_ICON_BYTES = 64 * 1024
