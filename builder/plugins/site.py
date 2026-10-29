# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""What plugins add to published pages.

A release may hold a `site.js` and a `site.css` next to its editor entry. Every
published page of the site loads them for each enabled plugin, so a plugin can
give visitors what the editor cannot: a scroll reveal, a counter, a parallax.
The editor never runs them.
"""

import frappe
from frappe.website.utils import clear_cache

from builder.plugins.access import INSTALLATION_DOCTYPE
from builder.plugins.constants import SITE_SCRIPT, SITE_STYLE

CACHE_KEY = "builder_plugin_site_assets"


def get_site_assets() -> dict[str, list[str]]:
	"""The site files of every enabled plugin, as URLs. Read on every page render, so cached."""
	return frappe.cache.get_value(CACHE_KEY, generator=collect_site_assets)


def collect_site_assets() -> dict[str, list[str]]:
	assets = {"scripts": [], "styles": []}
	for name in frappe.get_all(
		INSTALLATION_DOCTYPE, filters={"enabled": 1}, pluck="name", order_by="creation"
	):
		doc = frappe.get_cached_doc(INSTALLATION_DOCTYPE, name)
		if doc.install_state not in (None, "", "Ready") or not doc.release_path:
			continue
		for file, kind in ((SITE_SCRIPT, "scripts"), (SITE_STYLE, "styles")):
			if (doc.release_path / file).is_file():
				assets[kind].append(doc.release_file_url(file))
	return assets


def refresh_site_assets():
	"""Cached pages link the site files they were rendered with, so a change clears them."""
	before = frappe.cache.get_value(CACHE_KEY)
	after = collect_site_assets()
	frappe.cache.set_value(CACHE_KEY, after)
	if before != after:
		clear_cache()
