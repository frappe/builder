import os
import time
from typing import cast

import duckdb
import frappe
import pandas as pd

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


def _get_date_filter(from_date: str | None = None, to_date: str | None = None):
	if not from_date or not to_date:
		return ""

	# Add time component if not present
	if len(from_date) == 10:  # YYYY-MM-DD format
		from_date += " 00:00:00"
	if len(to_date) == 10:  # YYYY-MM-DD format
		to_date += " 23:59:59"

	return f"creation >= '{from_date}' AND creation <= '{to_date}'"


def _get_empty_analytics():
	return {"total_unique_views": 0, "total_views": 0, "data": [], "top_referrers": []}


def _get_route_filter(route: str | None = None, route_filter_type: str = "wildcard") -> str:
	"""Get route filter clause for SQL queries"""
	if not route:
		return ""

	if route_filter_type == "exact":
		return f"path = '{route}'"
	else:  # wildcard
		return f"path LIKE '%{route}%'"


def setup_duckdb_table(table_name=DUCKDB_TABLE):
	with DuckDBConnection() as db:
		sql_connection = frappe.db.get_connection()
		df = pd.read_sql(
			"SELECT creation, is_unique, path, referrer, time_zone, user_agent FROM `tabWeb Page View`",
			sql_connection,  # type: ignore
		)
		db.register("df", df)
		db.execute(
			f"CREATE OR REPLACE TABLE {table_name} AS SELECT creation, CAST(CASE WHEN is_unique = '' OR is_unique IS NULL THEN '0' ELSE CAST(is_unique AS VARCHAR) END AS INTEGER) as is_unique, path, referrer, time_zone, user_agent FROM df"
		)
		print(f"Successfully ingested {len(df)} records into DuckDB")


def ingest_web_page_views_to_duckdb(table_name=DUCKDB_TABLE):
	with DuckDBConnection() as db:
		table_exists = db.execute(
			f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
		).fetchone()
		if table_exists and table_exists[0] == 0:
			setup_duckdb_table(table_name)
			return

		result = db.execute(f"SELECT MAX(creation) FROM {table_name}").fetchone()
		last_record = result[0] if result and result[0] else None

		filters = {"creation": [">", last_record]} if last_record else {}

		total_count = frappe.db.count("Web Page View", filters=filters)
		print(f"Starting ingestion of {total_count} records...")

		page_size = 20000
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
				fields=["creation", "is_unique", "path", "referrer", "time_zone", "user_agent"],
				as_list=True,
				limit=page_size,
				order_by="creation asc",
			)

			if not records:
				break

			db.executemany(
				f"INSERT INTO {table_name} (creation, is_unique, path, referrer, time_zone, user_agent) VALUES (?, CAST(? AS INTEGER), ?, ?, ?, ?)",
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


def _get_interval_formats(interval):
	"""Get display and sort formats for time intervals"""
	display_formats = {
		"hourly": "%b %d, %I:00 %p",
		"daily": "%b %d, %Y",
		"weekly": "Week %W, %Y",
		"monthly": "%b %Y",
	}

	sort_formats = {
		"hourly": "%Y-%m-%d %H:00:00",
		"daily": "%Y-%m-%d",
		"weekly": "%Y-%W",
		"monthly": "%Y-%m",
	}

	return display_formats[interval], sort_formats.get(interval, display_formats[interval])


def _get_aggregated_views_query(where_clause, table_name=DUCKDB_TABLE):
	"""Get query for total and unique view counts"""
	return f"SELECT COUNT(*) as total_views, SUM(is_unique) as unique_views FROM {table_name} WHERE {where_clause}"


def _get_interval_views_query(where_clause, interval, table_name=DUCKDB_TABLE):
	"""Get query for views grouped by time interval"""
	display_fmt, sort_fmt = _get_interval_formats(interval)
	return f"""
		SELECT
			strftime('{display_fmt}', creation) as interval,
			COUNT(*) as total_page_views,
			SUM(is_unique) as unique_page_views
		FROM {table_name}
		WHERE {where_clause}
		GROUP BY interval, strftime('{sort_fmt}', creation)
		ORDER BY strftime('{sort_fmt}', creation)
	"""


def _get_referrer_domain_query(where_clause, limit=10, table_name=DUCKDB_TABLE):
	"""Get query for top referrer domains with counts"""
	return f"""
		WITH parsed_referrers AS (
			SELECT
				CASE
					WHEN referrer IS NULL OR referrer = '' THEN 'direct'
					WHEN REGEXP_MATCHES(referrer, '^https?://([^/]+)') THEN
						REGEXP_REPLACE(REGEXP_EXTRACT(referrer, '^https?://([^/]+)', 1), '^www\\.', '')
					ELSE 'direct'
				END as domain,
				is_unique
			FROM {table_name}
			WHERE {where_clause}
		)
		SELECT
			domain,
			COUNT(*) as total_count,
			SUM(is_unique) as unique_count
		FROM parsed_referrers
		GROUP BY domain
		ORDER BY total_count DESC
		LIMIT {limit}
	"""


def get_page_analytics(
	route=None,
	interval: str = "daily",
	table_name=DUCKDB_TABLE,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	"""Get analytics data for a specific page route or all pages"""
	try:
		# Get date filter
		date_filter = _get_date_filter(from_date, to_date)
		if not date_filter:
			return _get_empty_analytics()

		# Add route filter
		route_filter = _get_route_filter(route, route_filter_type)

		# Build WHERE clause properly
		where_conditions = []
		if date_filter:
			where_conditions.append(date_filter)
		if route_filter:
			where_conditions.append(route_filter)

		where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

		# Use provided interval or default to daily
		interval = interval or "daily"

		with DuckDBConnection() as db:
			# Get interval-based data
			interval_query = _get_interval_views_query(where_clause, interval, table_name)
			rows = db.execute(interval_query).fetchall()

			# Get total views
			total_query = _get_aggregated_views_query(where_clause, table_name)
			total_views, total_unique_views = db.execute(total_query).fetchone() or (0, 0)

			# Get top referrers for this specific page/route
			referrer_query = _get_referrer_domain_query(where_clause, 10, table_name)
			referrer_rows = db.execute(referrer_query).fetchall()

		return {
			"total_unique_views": total_unique_views or 0,
			"total_views": total_views or 0,
			"data": [{"interval": r[0], "total_page_views": r[1], "unique_page_views": r[2]} for r in rows],
			"top_referrers": [{"domain": r[0], "count": r[1]} for r in referrer_rows],
		}
	except Exception as e:
		frappe.log_error("DuckDB Analytics Error", str(e))
		return _get_empty_analytics()


def get_top_pages(
	table_name=DUCKDB_TABLE,
	route=None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	# Get date filter
	date_filter = _get_date_filter(from_date, to_date)
	route_filter = _get_route_filter(route, route_filter_type)

	# Build WHERE clause properly
	where_conditions = []
	if date_filter:
		where_conditions.append(date_filter)
	if route_filter:
		where_conditions.append(route_filter)

	where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

	with DuckDBConnection() as db:
		q = f"""
			SELECT path as route, COUNT(*) as view_count, SUM(is_unique) as unique_view_count
			FROM {table_name}
			{where_clause}
			GROUP BY path
			ORDER BY view_count DESC
			LIMIT 20
		"""
		rows = db.execute(q).fetchall()
		return [{"route": r[0], "view_count": r[1], "unique_view_count": r[2]} for r in rows]


def get_top_referrers(
	table_name=DUCKDB_TABLE,
	route=None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	"""Get top referrers from analytics data using SQL for domain extraction"""
	try:
		# Get date filter
		date_filter = _get_date_filter(from_date, to_date)
		route_filter = _get_route_filter(route, route_filter_type)

		# Build WHERE clause properly
		where_conditions = []
		if date_filter:
			where_conditions.append(date_filter)
		if route_filter:
			where_conditions.append(route_filter)

		where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

		with DuckDBConnection() as db:
			referrer_query = _get_referrer_domain_query(where_clause, 20, table_name)
			rows = db.execute(referrer_query).fetchall()
			return [{"domain": r[0], "count": r[1], "unique_count": r[2]} for r in rows]
	except Exception as e:
		frappe.log_error("DuckDB Analytics Error in top referrers", str(e))
		return []


def get_overall_analytics(
	interval: str = "daily",
	table_name=DUCKDB_TABLE,
	route=None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	"""Get overall site analytics with top pages and referrers"""
	analytics = get_page_analytics(
		route=route,
		interval=interval,
		table_name=table_name,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)
	analytics["top_pages"] = get_top_pages(
		table_name=table_name,
		route=route,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)
	analytics["top_referrers"] = get_top_referrers(
		table_name=table_name,
		route=route,
		from_date=from_date,
		to_date=to_date,
		route_filter_type=route_filter_type,
	)
	return analytics


def enqueue_web_page_view_ingesion():
	frappe.enqueue(
		"builder.builder_analytics.ingest_web_page_views_to_duckdb",
		queue="long",
	)
