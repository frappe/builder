# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What an extension may be named and hold.

Its own module, so the extension modules and the DocTypes share it without
importing each other.
"""

import re

# under the site's public files, which nginx and the dev server already serve at /files
EXTENSIONS_FOLDER = "builder_extensions"
MANIFEST_FILE = "manifest.json"
ENTRY_FILE = "main.js"

# The files a package may hold, by suffix. The editor imports the scripts as
# modules, and the rest are what those scripts load
ASSET_TYPES = {".js", ".css", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2"}

# publisher/name, lowercase. The slash is the only separator, and no install path
# is built from it, so a name can add no path segment.
EXTENSION_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")

# One SVG in the install root. No separator, so an icon names no file outside it.
ICON_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.svg$")

# An installation loaded from a dev server this session. It has no files, and the
# browser loads its entry from the dev server.
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

# The extension protocol this Builder speaks. 2 is a trusted extension, which
# runs in the editor's own Vue app. Protocol 1 ran in a sandboxed frame, so its
# packages import an SDK that this Builder does not serve.
PROTOCOL_VERSION = 2

# A `.builderext` package is one ZIP: the manifest, `main.js` and the icon at the
# root, and the build's `chunks/` and `assets/`. These bound what Builder will
# download and unpack from it. They match the Hub.
PACKAGE_FOLDERS = frozenset({"chunks", "assets"})
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_BYTES = 30 * 1024 * 1024
MAX_PACKAGE_FILES = 200
MAX_MANIFEST_BYTES = 128 * 1024
MAX_ICON_BYTES = 64 * 1024
