import os

import duckdb
import frappe
import pandas as pd

DUCKDB_TABLE = "web_page_views"
CLICKS_TABLE = "web_page_clicks"


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


def get_date_filter(from_date: str | None = None, to_date: str | None = None) -> tuple[str, list]:
	"""Return a parameterized date filter clause and its bind values."""
	if not from_date or not to_date:
		return "", []

	# Add time component if not present
	if len(from_date) == 10:  # YYYY-MM-DD format
		from_date += " 00:00:00"
	if len(to_date) == 10:  # YYYY-MM-DD format
		to_date += " 23:59:59"

	return "creation >= CAST(? AS TIMESTAMP) AND creation <= CAST(? AS TIMESTAMP)", [from_date, to_date]


def get_empty_analytics():
	return {"total_unique_views": 0, "total_views": 0, "data": [], "top_referrers": []}


def get_empty_ctr():
	return {"total_views": 0, "total_clicks": 0, "ctr": 0, "elements": []}


def get_route_filter(route: str | None = None, route_filter_type: str = "wildcard") -> tuple[str, list]:
	"""Return a parameterized route filter clause and its bind values."""
	if not route:
		return "", []

	if route_filter_type == "exact":
		return "path = ?", [route]
	else:  # wildcard
		return "path LIKE ?", [f"%{route}%"]


def build_where_clause(
	route: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
) -> tuple[str, list]:
	"""Combine the date and route filters into a single WHERE clause and ordered params."""
	conditions = []
	params: list = []

	date_clause, date_params = get_date_filter(from_date, to_date)
	if date_clause:
		conditions.append(date_clause)
		params += date_params

	route_clause, route_params = get_route_filter(route, route_filter_type)
	if route_clause:
		conditions.append(route_clause)
		params += route_params

	where_clause = " AND ".join(conditions) if conditions else "1=1"
	return where_clause, params


def setup_duckdb_table(table_name=DUCKDB_TABLE):
	with DuckDBConnection() as db:
		sql_connection = frappe.db.get_connection()
		df = pd.read_sql(
			"SELECT creation, is_unique, path, referrer, time_zone, user_agent FROM `tabWeb Page View`",
			sql_connection,  # type: ignore
		)
		db.register("df", df)
		db.execute(
			f"CREATE OR REPLACE TABLE {table_name} AS SELECT TRY_CAST(creation AS TIMESTAMP) as creation, CAST(CASE WHEN is_unique = '' OR is_unique IS NULL THEN '0' ELSE CAST(is_unique AS VARCHAR) END AS INTEGER) as is_unique, CAST(path AS VARCHAR) as path, CAST(referrer AS VARCHAR) as referrer, CAST(time_zone AS VARCHAR) as time_zone, CAST(user_agent AS VARCHAR) as user_agent FROM df"
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

		# Recreate table if creation column has a stale/incompatible type (not TIMESTAMP)
		col_type = db.execute(
			f"SELECT data_type FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = 'creation'"
		).fetchone()
		if col_type and col_type[0].upper() != "TIMESTAMP":
			print(f"Recreating {table_name}: creation column type is {col_type[0]}, expected TIMESTAMP")
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
				f"INSERT INTO {table_name} (creation, is_unique, path, referrer, time_zone, user_agent) VALUES (TRY_CAST(? AS TIMESTAMP), CAST(COALESCE(NULLIF(?, ''), '0') AS INTEGER), ?, ?, ?, ?)",
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


def get_interval_formats(interval):
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

	# Guard against unknown intervals (these strings end up in SQL format strings)
	if interval not in display_formats:
		interval = "daily"

	return display_formats[interval], sort_formats.get(interval, display_formats[interval])


def get_aggregated_views_query(where_clause, table_name=DUCKDB_TABLE):
	"""Get query for total and unique view counts"""
	return f"SELECT COUNT(*) as total_views, SUM(is_unique) as unique_views FROM {table_name} WHERE {where_clause}"


def get_interval_views_query(where_clause, interval, table_name=DUCKDB_TABLE):
	"""Get query for views grouped by time interval"""
	display_fmt, sort_fmt = get_interval_formats(interval)
	return f"""
		SELECT
			strftime('{display_fmt}', creation) as interval,
			COUNT(*) as total_page_views,
			SUM(is_unique) as unique_page_views
		FROM {table_name}
		WHERE ({where_clause}) AND creation IS NOT NULL
		GROUP BY interval, strftime('{sort_fmt}', creation)
		ORDER BY strftime('{sort_fmt}', creation)
	"""


def get_referrer_domain_query(where_clause, limit=10, table_name=DUCKDB_TABLE):
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
		# A date range is required for page analytics
		date_filter, _ = get_date_filter(from_date, to_date)
		if not date_filter:
			return get_empty_analytics()

		where_clause, params = build_where_clause(route, from_date, to_date, route_filter_type)

		# Use provided interval or default to daily
		interval = interval or "daily"

		with DuckDBConnection() as db:
			# Get interval-based data
			interval_query = get_interval_views_query(where_clause, interval, table_name)
			rows = db.execute(interval_query, params).fetchall()

			# Get total views
			total_query = get_aggregated_views_query(where_clause, table_name)
			total_views, total_unique_views = db.execute(total_query, params).fetchone() or (0, 0)

			# Get top referrers for this specific page/route
			referrer_query = get_referrer_domain_query(where_clause, 10, table_name)
			referrer_rows = db.execute(referrer_query, params).fetchall()

		return {
			"total_unique_views": total_unique_views or 0,
			"total_views": total_views or 0,
			"data": [{"interval": r[0], "total_page_views": r[1], "unique_page_views": r[2]} for r in rows],
			"top_referrers": [{"domain": r[0], "count": r[1]} for r in referrer_rows],
		}
	except Exception as e:
		frappe.log_error("DuckDB Analytics Error", str(e))
		return get_empty_analytics()


def get_top_pages(
	table_name=DUCKDB_TABLE,
	route=None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	try:
		inner_clause, params = build_where_clause(route, from_date, to_date, route_filter_type)
		where_clause = "" if inner_clause == "1=1" else f"WHERE {inner_clause}"

		with DuckDBConnection() as db:
			q = f"""
				SELECT path as route, COUNT(*) as view_count, SUM(is_unique) as unique_view_count
				FROM {table_name}
				{where_clause}
				GROUP BY path
				ORDER BY view_count DESC
				LIMIT 20
			"""
			rows = db.execute(q, params).fetchall()
			return [{"route": r[0], "view_count": r[1], "unique_view_count": r[2]} for r in rows]
	except Exception as e:
		frappe.log_error("DuckDB Analytics Error in top pages", str(e))
		return []


def get_top_referrers(
	table_name=DUCKDB_TABLE,
	route=None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	"""Get top referrers from analytics data using SQL for domain extraction"""
	try:
		where_clause, params = build_where_clause(route, from_date, to_date, route_filter_type)

		with DuckDBConnection() as db:
			referrer_query = get_referrer_domain_query(where_clause, 20, table_name)
			rows = db.execute(referrer_query, params).fetchall()
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


CLICK_FIELDS = ["creation", "is_unique", "path", "element", "tag", "text", "href", "visitor_id"]


def setup_clicks_table(table_name=CLICKS_TABLE):
	with DuckDBConnection() as db:
		sql_connection = frappe.db.get_connection()
		df = pd.read_sql(
			"SELECT creation, is_unique, path, element, tag, text, href, visitor_id FROM `tabBuilder Page Click`",
			sql_connection,  # type: ignore
		)
		db.register("df", df)
		db.execute(
			f"CREATE OR REPLACE TABLE {table_name} AS SELECT TRY_CAST(creation AS TIMESTAMP) as creation, CAST(CASE WHEN is_unique = '' OR is_unique IS NULL THEN '0' ELSE CAST(is_unique AS VARCHAR) END AS INTEGER) as is_unique, CAST(path AS VARCHAR) as path, CAST(element AS VARCHAR) as element, CAST(tag AS VARCHAR) as tag, CAST(text AS VARCHAR) as text, CAST(href AS VARCHAR) as href, CAST(visitor_id AS VARCHAR) as visitor_id FROM df"
		)
		print(f"Successfully ingested {len(df)} click records into DuckDB")


def ingest_clicks_to_duckdb(table_name=CLICKS_TABLE):
	with DuckDBConnection() as db:
		table_exists = db.execute(
			f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
		).fetchone()
		if table_exists and table_exists[0] == 0:
			setup_clicks_table(table_name)
			return

		col_type = db.execute(
			f"SELECT data_type FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = 'creation'"
		).fetchone()
		if col_type and col_type[0].upper() != "TIMESTAMP":
			print(f"Recreating {table_name}: creation column type is {col_type[0]}, expected TIMESTAMP")
			setup_clicks_table(table_name)
			return

		page_size = 20000
		db.begin()

		while True:
			result = db.execute(f"SELECT MAX(creation) FROM {table_name}").fetchone()
			last_record = result[0] if result and result[0] else None

			filters = {"creation": [">", last_record]} if last_record else {}
			records = frappe.get_all(
				"Builder Page Click",
				filters=filters,
				fields=["creation", "is_unique", "path", "element", "tag", "text", "href", "visitor_id"],
				as_list=True,
				limit=page_size,
				order_by="creation asc",
			)

			if not records:
				break

			db.executemany(
				f"INSERT INTO {table_name} (creation, is_unique, path, element, tag, text, href, visitor_id) "
				f"VALUES (TRY_CAST(? AS TIMESTAMP), CAST(COALESCE(NULLIF(?, ''), '0') AS INTEGER), ?, ?, ?, ?, ?, ?)",
				records,
			)

			if len(records) < page_size:
				break

		db.commit()


def enqueue_click_ingestion():
	frappe.enqueue(
		"builder.builder_analytics.ingest_clicks_to_duckdb",
		queue="long",
	)


def get_page_ctr(
	route: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	route_filter_type: str = "wildcard",
):
	"""Click-through rate per page/element: clicks (from web_page_clicks) over page views
	(from web_page_views), joined on the shared `path`."""
	try:
		date_filter, _ = get_date_filter(from_date, to_date)
		if not date_filter:
			return get_empty_ctr()

		where_clause, params = build_where_clause(route, from_date, to_date, route_filter_type)

		with DuckDBConnection() as db:
			total_views = (
				db.execute(f"SELECT COUNT(*) FROM {DUCKDB_TABLE} WHERE {where_clause}", params).fetchone()[0]
				or 0
			)
			total_clicks = (
				db.execute(f"SELECT COUNT(*) FROM {CLICKS_TABLE} WHERE {where_clause}", params).fetchone()[0]
				or 0
			)

			# element label falls back element-name -> visible text -> href -> tag
			element_rows = db.execute(
				f"""
				WITH clicks AS (
					SELECT
						path,
						COALESCE(NULLIF(element, ''), NULLIF(text, ''), NULLIF(href, ''), tag) AS label,
						ANY_VALUE(tag) AS tag,
						ANY_VALUE(text) AS text,
						ANY_VALUE(href) AS href,
						COUNT(*) AS clicks,
						SUM(is_unique) AS unique_clicks
					FROM {CLICKS_TABLE}
					WHERE {where_clause}
					GROUP BY path, label
				),
				views AS (
					SELECT path, COUNT(*) AS views FROM {DUCKDB_TABLE} WHERE {where_clause} GROUP BY path
				)
				SELECT clicks.label, clicks.tag, clicks.text, clicks.href, clicks.path,
					clicks.clicks, clicks.unique_clicks, COALESCE(views.views, 0) AS views
				FROM clicks
				LEFT JOIN views ON clicks.path = views.path
				ORDER BY clicks.clicks DESC
				LIMIT 50
				""",
				params + params,
			).fetchall()

		return {
			"total_views": total_views,
			"total_clicks": total_clicks,
			"ctr": round(total_clicks / total_views * 100, 2) if total_views else 0,
			"elements": [
				{
					"label": r[0],
					"tag": r[1],
					"text": r[2],
					"href": r[3],
					"route": r[4],
					"clicks": r[5],
					"unique_clicks": r[6],
					"views": r[7],
					"ctr": round(r[5] / r[7] * 100, 2) if r[7] else 0,
				}
				for r in element_rows
			],
		}
	except Exception as e:
		frappe.log_error("DuckDB CTR Error", str(e))
		return get_empty_ctr()
