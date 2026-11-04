# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import shutil
import unittest

from frappe.tests.utils import FrappeTestCase

from builder.plugins.bob import syntax_error


@unittest.skipUnless(shutil.which("node"), "the check runs only where node is installed")
class TestPluginSyntaxCheck(FrappeTestCase):
	def test_valid_code_passes(self):
		self.assertIsNone(syntax_error("export default { install() {} }"))

	def test_a_syntax_error_names_the_entry_file_and_line(self):
		message = syntax_error("export default {\n\tinstall() {\n}")
		self.assertIn("main.js:3", message)
		self.assertIn("SyntaxError", message)
