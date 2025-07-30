import os

import duckdb
import frappe
import frappe.utils

DUCKDB_TABLE = "web_page_views"


class DuckDBConnection:
	def __init__(self):
		self.db = None

	def __enter__(self):
		duckdb_path = os.path.join(frappe.get_site_path(), "builder_analytics.duckdb")
		self.db = duckdb.connect(duckdb_path)
		return self.db

	def __exit__(self, exc_type, exc_val, exc_tb):
		if self.db:
			self.db.close()


def _create_duckdb_table(db, table_name=DUCKDB_TABLE):
	db.execute(f"""
		CREATE TABLE IF NOT EXISTS {table_name} (
			creation TIMESTAMP,
			is_unique INTEGER,
			path TEXT,
			referrer TEXT
		)
	""")


def _get_date_range_filter(date_range: str = "last_30_days"):
	date_config = _get_date_config(date_range)
	if not date_config:
		return "", None, None
	to_date = frappe.utils.now_datetime()
	from_date = _calculate_from_date(to_date, date_config)
	where = f"creation >= '{from_date}' AND creation <= '{to_date}'"
	return where, from_date, to_date


def _get_empty_analytics():
	return {"total_unique_views": 0, "total_views": 0, "data": []}


def _get_date_config(date_range):
	return {
		"today": {"delta": -24, "unit": "hours", "default_interval": "hourly"},
		"this_week": {"delta": -7, "unit": "days", "default_interval": "daily"},
		"last_7_days": {"delta": -7, "unit": "days", "default_interval": "daily"},
		"last_30_days": {"delta": -30, "unit": "days", "default_interval": "daily"},
		"last_90_days": {"delta": -90, "unit": "days", "default_interval": "weekly"},
		"last_180_days": {"delta": -180, "unit": "days", "default_interval": "weekly"},
		"this_year": {"delta": None, "unit": None, "default_interval": "monthly"},
	}.get(date_range)


def _calculate_from_date(to_date, config):
	if config["delta"] is None:  # Handle "this_year" case
		return frappe.utils.get_datetime(f"{to_date.year}-01-01")
	return frappe.utils.add_to_date(to_date, **{config["unit"]: config["delta"]})


def reset_duckdb_table(table_name=DUCKDB_TABLE):
	with DuckDBConnection() as db:
		db.execute(f"DROP TABLE IF EXISTS {table_name}")
		_create_duckdb_table(db, table_name)

	# Re-ingest all data
	ingest_web_page_views_to_duckdb(table_name)


def ingest_web_page_views_to_duckdb(table_name=DUCKDB_TABLE):
	with DuckDBConnection() as db:
		_create_duckdb_table(db, table_name)
		result = db.execute(f"SELECT MAX(creation) FROM {table_name}").fetchone()
		last_record = result[0] if result and result[0] else None

		filters = {"creation": [">", last_record]} if last_record else {}

		total_count = frappe.db.count("Web Page View", filters=filters)
		print(f"Starting ingestion of {total_count} records...")

		page_size = 10000
		start = 0
		processed = 0

		db.begin()

		while True:
			result = db.execute(f"SELECT MAX(creation) FROM {table_name}").fetchone()
			last_record = result[0] if result and result[0] else None

			filters = {"creation": [">", last_record]} if last_record else {}
			records = frappe.get_all(
				"Web Page View",
				filters=filters,
				fields=["creation", "is_unique", "path", "referrer"],
				as_list=True,
				limit=page_size,
				order_by="creation asc",
			)

			if not records:
				break

			db.executemany(
				f"INSERT INTO {table_name} (creation, is_unique, path, referrer) VALUES (?, ?, ?, ?)",
				records,
			)

			processed += len(records)
			progress = (processed / total_count) * 100 if total_count > 0 else 100
			print(f"Progress: {processed}/{total_count} ({progress:.1f}%) records ingested")

			if len(records) < page_size:
				break

			start += page_size

		db.commit()
		print(f"Successfully ingested {processed} records into DuckDB")


def get_page_analytics(route=None, date_range: str = "last_30_days", interval=None, table_name=DUCKDB_TABLE):
	"""Get analytics data for a specific page route or all pages"""
	try:
		date_config = _get_date_config(date_range)
		if not date_config:
			return _get_empty_analytics()

		where, from_date, to_date = _get_date_range_filter(date_range)
		if route:
			where += f" AND path = '{route}'"

		interval = interval or date_config["default_interval"]
		fmt = {
			"hourly": "%b %d, %I:00 %p",
			"daily": "%b %d, %Y",
			"weekly": "Week %W, %Y",
			"monthly": "%b %Y",
		}[interval]

		with DuckDBConnection() as db:
			sort_formats = {
				"hourly": "%Y-%m-%d %H:00:00",
				"daily": "%Y-%m-%d",
				"weekly": "%Y-%W",
				"monthly": "%Y-%m",
			}

			sort_fmt = sort_formats.get(interval, fmt)

			# Use sort format for ordering when different from display format
			q = f"""
			SELECT
				strftime('{fmt}', creation) as interval,
				COUNT(*) as total_page_views,
				SUM(is_unique) as unique_page_views
			FROM {table_name}
			WHERE {where}
			GROUP BY interval, strftime('{sort_fmt}', creation)
			ORDER BY strftime('{sort_fmt}', creation)
			"""
			rows = db.execute(q).fetchall()

			# Total views
			q2 = f"SELECT COUNT(*), SUM(is_unique) FROM {table_name} WHERE {where}"
			total_views, total_unique_views = db.execute(q2).fetchone() or (0, 0)

		return {
			"total_unique_views": total_unique_views or 0,
			"total_views": total_views or 0,
			"data": [{"interval": r[0], "total_page_views": r[1], "unique_page_views": r[2]} for r in rows],
		}
	except Exception as e:
		frappe.log_error("DuckDB Analytics Error", str(e))
		return _get_empty_analytics()


def get_top_pages(date_range: str = "last_30_days", table_name=DUCKDB_TABLE):
	where, _, _ = _get_date_range_filter(date_range)
	with DuckDBConnection() as db:
		q = f"""
			SELECT path as route, COUNT(*) as view_count, SUM(is_unique) as unique_view_count
			FROM {table_name}
			WHERE {where}
			GROUP BY path
			ORDER BY view_count DESC
			LIMIT 20
		"""
		rows = db.execute(q).fetchall()
		return [{"route": r[0], "view_count": r[1], "unique_view_count": r[2]} for r in rows]


def get_top_referrers(date_range: str = "last_30_days", table_name=DUCKDB_TABLE):
	"""Get top referrers from analytics data using SQL for domain extraction"""
	try:
		where, _, _ = _get_date_range_filter(date_range)
		with DuckDBConnection() as db:
			q = f"""
				WITH parsed_referrers AS (
					SELECT
						CASE
							WHEN referrer IS NULL OR referrer = '' THEN 'direct'
							WHEN REGEXP_MATCHES(referrer, '^https?://([^/]+)') THEN
								REGEXP_EXTRACT(referrer, '^https?://([^/]+)', 1)
							ELSE 'direct'
						END as domain,
						is_unique
					FROM {table_name}
					WHERE {where}
				)
				SELECT
					domain,
					COUNT(*) as total_count,
					SUM(is_unique) as unique_count
				FROM parsed_referrers
				GROUP BY domain
				ORDER BY total_count DESC
				LIMIT 20
			"""
			rows = db.execute(q).fetchall()
			return [{"domain": r[0], "count": r[1], "unique_count": r[2]} for r in rows]
	except Exception as e:
		frappe.log_error("DuckDB Analytics Error in top referrers", str(e))
		return []


def get_overall_analytics(date_range: str = "last_30_days", interval=None, table_name=DUCKDB_TABLE):
	"""Get overall site analytics with top pages and referrers"""
	analytics = get_page_analytics(None, date_range, interval, table_name)
	analytics["top_pages"] = get_top_pages(date_range=date_range, table_name=table_name)
	analytics["top_referrers"] = get_top_referrers(date_range=date_range, table_name=table_name)
	return analytics


def enqueue_web_page_view_ingesion():
	frappe.enqueue(
		"builder.builder_analytics.ingest_web_page_views_to_duckdb",
		queue="long",
	)
