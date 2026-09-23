# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What an extension may be named, hold, and ask for.

Its own module, so the extension modules and the DocTypes share it without
importing each other.
"""

import re

EXTENSIONS_FOLDER = "extensions"
ENTRY_FILE = "main.js"

# publisher/name, lowercase. The slash is the only separator, and no install path
# is built from it, so a name can add no path segment.
EXTENSION_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")

# One SVG in the install root. No separator, so an icon names no file outside it.
# No other format, so the editor draws it in an <img> at any size.
ICON_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.svg$")

# every capability the bridge gates a method by
CAPABILITIES = (
	"context.read",
	"block.read",
	"block.update",
	"block.insert",
	"page.read",
	"page.write",
	"token.write",
	"ui.dialog",
	"ui.popover",
	"data.access",
	"schema.write",
)

# An installation loaded from a dev server this session. It has no files, and the
# browser adds its own entry for it, so the listing leaves it out.
DEV_EXTENSION_VERSION = "0.0.0-dev"

# The editor holds the whole entry in memory and posts it to five frames. The
# ceiling is what a browser can hold, not what a disk can.
MAX_SOURCE_BYTES = 5_000_000

# A README is prose, and the panel renders it in a 300 pixel column. This is room
# for a long one and no room for a book.
MAX_README_BYTES = 100_000

# Room for settings and a cached list. Small enough that no extension fills a
# site with what it remembers.
MAX_STATE_BYTES = 100_000
