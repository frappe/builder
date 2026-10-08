# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Names, file types and limits for extensions.

The extension modules and the DocTypes use this module. So they do not import each other."""

import re

EXTENSIONS_FOLDER = "extensions"
ENTRY_FILE = "main.js"

# The route for the SDK and the installed files of extensions
ASSET_ROUTE = "builder_extension_asset"

# The file types that a frame can load.
# No HTML or XML. A file must not open as a page of the site.
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

# publisher/name, in lowercase. The install path does not use the name.
EXTENSION_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")

# One SVG file in the install root. The pattern has no slash.
# So the icon cannot name a file outside the install.
ICON_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.svg$")

# The permissions that the bridge checks. Reads and windows need no permission.
PERMISSIONS = (
	"page.edit",
	"page.write",
	"token.write",
	"data.access",
	"schema.write",
	"method.call",
)

# The version of an extension from a dev server. It has no files.
# The list of installations does not show it, because the browser adds it.
DEV_EXTENSION_VERSION = "0.0.0-dev"

# The panel shows the README in a narrow column. This limit is enough for a long README.
MAX_README_BYTES = 100_000

# Enough for settings and a small cache. An extension cannot fill the site with state.
MAX_STATE_BYTES = 100_000
