"""Templates moved out of builder into the builder_hub app (fetched over HTTP).

Delete the template-group pages that builder used to sync into every site's DB,
so the old curated templates don't linger in the local picker. Preserve the
user's own "My Templates" (is_template=1 with no template_group). Leave the
groups' shared components/variables in place — a page a user already created
from a template may still reference them.
"""

import frappe


def execute():
	# The hub site WANTS its template-group pages (they are its source of truth,
	# and deleting them in dev mode would rmtree the committed fixtures via
	# on_trash). Only consuming sites get cleaned.
	if "builder_hub" in frappe.get_installed_apps():
		return

	if not frappe.db.has_column("Builder Page", "template_group"):
		return

	pages = frappe.get_all(
		"Builder Page",
		filters={"is_template": 1, "template_group": ("is", "set")},
		pluck="name",
	)
	for name in pages:
		frappe.delete_doc("Builder Page", name, force=True, ignore_permissions=True)
