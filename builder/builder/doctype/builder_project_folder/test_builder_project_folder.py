# Copyright (c) 2025, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase

from builder.builder.doctype.builder_project_folder.builder_project_folder import is_system_activity

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestBuilderProjectFolder(IntegrationTestCase):
	"""
	Integration tests for BuilderProjectFolder.
	Use this class for testing interactions between multiple components.
	"""

	def test_tests_count_as_system_activity(self):
		self.assertTrue(is_system_activity())
