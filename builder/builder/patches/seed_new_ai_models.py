# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Seed models added to the shortlist after a site already ran the original seed.

A patch runs once per site, so extending seed_ai_providers_and_models' list only
ever reaches fresh installs. That seeder creates just what is missing, so
re-running it is the whole fix.
"""

from builder.builder.patches.seed_ai_providers_and_models import execute as seed_shortlist


def execute():
	seed_shortlist()
