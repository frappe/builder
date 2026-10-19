import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder_analytics import CLICK_FIELDS, VIEW_FIELDS, DuckDBConnection, setup_table

TEST_TABLE = "test_snapshot"


class TestBuilderAnalytics(FrappeTestCase):
	def tearDown(self):
		with DuckDBConnection() as db:
			db.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")

	def test_setup_table_snapshots_the_doctype(self):
		frappe.get_doc(
			{"doctype": "Builder Page Click", "path": "snapshot-test", "element": "button", "is_unique": 1}
		).insert(ignore_permissions=True)

		setup_table(TEST_TABLE, "Builder Page Click", CLICK_FIELDS)

		with DuckDBConnection(read_only=True) as db:
			rows = db.execute(
				f"SELECT element, is_unique FROM {TEST_TABLE} WHERE path = 'snapshot-test'"
			).fetchall()
		self.assertEqual(rows, [("button", 1)])

	def test_setup_table_snapshots_every_web_page_view(self):
		# more than get_all's default page of 20
		for _ in range(25):
			view = frappe.get_doc({"doctype": "Web Page View", "path": "snapshot-test"}).insert(
				ignore_permissions=True
			)
			self.addCleanup(view.delete, ignore_permissions=True)

		setup_table(TEST_TABLE, "Web Page View", VIEW_FIELDS)

		with DuckDBConnection(read_only=True) as db:
			rows = db.execute(f"SELECT COUNT(*) FROM {TEST_TABLE} WHERE path = 'snapshot-test'").fetchall()
		self.assertEqual(rows, [(25,)])
