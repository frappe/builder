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

	def test_setup_table_reads_web_page_views(self):
		setup_table(TEST_TABLE, "Web Page View", VIEW_FIELDS)

		with DuckDBConnection(read_only=True) as db:
			columns = db.execute(
				f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{TEST_TABLE}'"
			).fetchall()
		self.assertEqual([name for name, _ in columns], VIEW_FIELDS)
		self.assertEqual(dict(columns)["creation"], "TIMESTAMP")
