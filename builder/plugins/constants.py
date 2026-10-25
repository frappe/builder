# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What a plugin may be named and hold.

Its own module, so the plugin modules and the DocTypes share it without
importing each other.
"""

import re

# under the site's public files, which nginx and the dev server already serve at /files
PLUGINS_FOLDER = "builder_plugins"
MANIFEST_FILE = "manifest.json"
ENTRY_FILE = "main.js"

# The files a package may hold, by suffix. The editor imports the scripts as
# modules, and the rest are what those scripts load
ASSET_TYPES = {".js", ".css", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2"}

# publisher/name, lowercase. The slash is the only separator, and no install path
# is built from it, so a name can add no path segment.
PLUGIN_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*")
VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")

# One SVG in the install root. No separator, so an icon names no file outside it.
ICON_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.svg")

# The first 12 hex digits of the package sha256. It names the release folder and the
# entry URL, so it must hold no path segment.
CHECKSUM_PATTERN = re.compile(r"[0-9a-f]{12}")

# An installation loaded from a dev server this session. It has no files, and the
# browser loads its entry from the dev server.
DEV_PLUGIN_VERSION = "0.0.0-dev"

# A README is prose, and the panel renders it in a 300 pixel column. This is room
# for a long one and no room for a book.
MAX_README_BYTES = 100_000

# Room for settings and a cached list. Small enough that no plugin fills a
# site with what it remembers.
MAX_STATE_BYTES = 100_000

# The largest file a package may hold. It matches the Hub.
MAX_FILE_BYTES = 5 * 1024 * 1024

# The Builder Hub a site reads its catalog from when the site config sets no
# `builder_hub_url`.
DEFAULT_HUB_URL = "https://preview.frappe.cloud"

# The plugin protocol this Builder speaks. A release that needs a newer one is
# refused, and the Hub is asked for a release at or below this.
PROTOCOL_VERSION = 1

# A `.builderplugin` package is one ZIP: the manifest, `main.js` and the icon at the
# root, and the build's `chunks/` and `assets/`. These bound what Builder will
# download and unpack from it. They match the Hub.
PACKAGE_FOLDERS = frozenset({"chunks", "assets"})
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_BYTES = 30 * 1024 * 1024
MAX_PACKAGE_FILES = 200
MAX_MANIFEST_BYTES = 128 * 1024
MAX_ICON_BYTES = 64 * 1024
