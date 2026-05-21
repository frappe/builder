---
description: "Use when writing, editing, or reviewing Python code: Frappe doctypes, API endpoints, controller lifecycle hooks, database queries, permissions, background jobs, scheduled tasks, or hooks.py. Covers Frappe framework conventions and Frappe Builder backend patterns."
applyTo: "builder/**/*.py"
---

# Backend Conventions — Frappe Builder

## Stack

- **Python ≥ 3.10** with full type annotations
- **Frappe Framework** — DocType ORM, website generator, Jinja templating
- **Black** (line-length 99) + **isort** + **Ruff** (line-length 110, target py310)
- Backend source: `builder/builder/`

---

## Code Style

```python
# ✅ Tabs, trailing comma, type annotations
def get_page_data(
	page_name: str,
	include_draft: bool = False,
) -> dict:
	page = frappe.get_cached_doc("Builder Page", page_name)
	return {"blocks": page.blocks, "route": page.route}
```

- **Tabs** for indentation (pyproject.toml: `indent = "\t"`)
- **Trailing comma** in multi-line function signatures and imports
- **Type annotations** on all function parameters and return values
- Line length: 99 (Black) / 110 (Ruff)

---

## Doctype Structure

Every doctype lives in `builder/builder/doctype/<doctype_name>/` with:
- `<doctype>.json` — schema (fields, permissions, layout)
- `<doctype>.py` — controller class extending `Document` or a base class
- `test_<doctype>.py` — test class (extend `FrappeTestCase`)

```python
# builder/builder/doctype/builder_page/builder_page.py
import frappe
from frappe.website.website_generator import WebsiteGenerator

class BuilderPage(WebsiteGenerator):
    def before_insert(self):
        self.process_blocks()
        self.set_default_values()

    def on_update(self):
        self.clear_cache()

    def on_trash(self):
        self.cleanup_assets()

    def get_context(self, context):
        # Provides Jinja template context for public page render
        context.page = self
```

**Lifecycle hook order**: `onload → validate → before_insert → after_insert → on_update → on_trash`

---

## API Endpoints

All public Python functions called from the frontend must use `@frappe.whitelist()`. Always check permissions explicitly — the decorator alone does not enforce them.

```python
@frappe.whitelist()
def get_page_preview_html(page: str) -> str:
    if not frappe.has_permission("Builder Page", "read", page):
        frappe.throw("You do not have permission to view this page")
    doc = frappe.get_cached_doc("Builder Page", page)
    return doc.render_html()
```

Frontend calls these at `/api/method/<dotted.module.path>`.

**Custom decorator for write permission** (defined in `builder/utils.py`):
```python
from builder.utils import has_page_write

@frappe.whitelist()
@has_page_write()
def publish_page(page: str) -> None:
    doc = frappe.get_doc("Builder Page", page)
    doc.published = 1
    doc.save()
```

---

## Database Access

Prefer cached and list-based access. Avoid raw SQL except in analytics.

| Pattern | When |
|---------|------|
| `frappe.get_cached_doc(doctype, name)` | Read-only lookups (Redis-cached) |
| `frappe.get_doc(doctype, name)` | When you need to call `.save()` or modify |
| `frappe.get_list(doctype, fields, filters)` | List queries |
| `frappe.db.get_value(doctype, filters, fieldname)` | Single field, no doc load |
| `frappe.db.set_value(doctype, name, field, value)` | Single field update without full doc |

```python
# ✅ Cached read
page = frappe.get_cached_doc("Builder Page", page_name)

# ✅ List query
pages = frappe.get_list(
    "Builder Page",
    filters={"published": 1},
    fields=["name", "route", "page_title"],
    order_by="modified desc",
    limit=50,
)

# ✅ Single field
route = frappe.db.get_value("Builder Page", page_name, "route")
```

---

## Error Handling

Never use bare `raise Exception(...)`. Use Frappe's error utilities so the framework serializes them as JSON HTTP responses.

```python
# ✅ correct
frappe.throw("You do not have permission to edit this page")
frappe.throw(_("Page {0} not found").format(page_name), frappe.DoesNotExistError)

# Permission-specific
if not frappe.has_permission("Builder Page", "write", doc):
    frappe.throw("Insufficient permissions", frappe.PermissionError)

# Role-based guard
frappe.only_for("System Manager")
```

---

## Permissions

- Defined in the doctype `.json` `permissions` array (role + perm_type + level)
- Always call `frappe.has_permission()` at the start of sensitive functions
- `frappe.session.user` gives the current user
- Use the `has_page_write` decorator from `builder.utils` for page-write checks

```python
@frappe.whitelist()
def delete_page(page: str) -> None:
    frappe.has_permission("Builder Page", "delete", page, throw=True)
    frappe.delete_doc("Builder Page", page)
```

---

## Background Jobs

Use `frappe.enqueue_doc()` for async tasks on a document. Use `frappe.enqueue()` for module-level functions.

```python
# Async task on a document method
frappe.enqueue_doc(
    doc.doctype,
    doc.name,
    "generate_page_preview_image",
    html=html_content,
    queue="short",         # "short" | "default" | "long"
    now=frappe.flags.in_test,  # run synchronously in tests
)

# Async module-level function
frappe.enqueue(
    "builder.builder_analytics.ingest_web_page_views_to_duckdb",
    queue="long",
)
```

---

## Scheduled Tasks

Add entries to `scheduler_events` in `hooks.py`:

```python
scheduler_events = {
    "cron": {
        "*/10 * * * *": ["builder.builder_analytics.ingest_web_page_views_to_duckdb"],
    },
    "daily": ["builder.tasks.daily_cleanup"],
}
```

---

## hooks.py Conventions

Add website generators, jinja filters, and other Frappe integrations here — never in `__init__.py`.

```python
# hooks.py
website_generators = ["Builder Page"]   # creates /page/<route> URLs

jinja = {
    "filters": ["builder.utils.combine", "builder.utils.hash"],
    "methods": [],
}

scheduler_events = { ... }

after_migrate = "builder.install.after_migrate"
```

---

## Doctype JSON Schema

When adding/modifying fields, edit the `.json` directly (or use Frappe Desk → DocType editor and export). Key conventions:
- `fieldtype`: `"Data"`, `"Long Text"`, `"Code"`, `"JSON"`, `"Link"`, `"Check"`, etc.
- `in_list_view: 1` / `in_standard_filter: 1` for list/search fields
- `read_only: 1` for computed/auto fields
- Child tables use `fieldtype: "Table"` with `options: "<ChildDoctype>"`

---

## Performance

Performance is non-negotiable. Every backend change that affects page rendering or API response time must be justified.

### Caching
- **`frappe.get_cached_doc()`** for any read-only doc lookup — it uses Redis. Only use `frappe.get_doc()` when you need to call `.save()` or modify the doc.
- **`frappe.db.get_value()`** over loading a full document when only one or two fields are needed.
- **`@redis_cache`** decorator (from `frappe.utils.caching`) for expensive computed results that are stable across requests:
  ```python
  from frappe.utils.caching import redis_cache

  @redis_cache(ttl=60 * 60)  # seconds
  def get_all_published_routes() -> list[str]:
      return frappe.get_all("Builder Page", filters={"published": 1}, pluck="route")
  ```

### DB queries
- Always specify `fields=["name", "route"]` — **never** `fields=["*"]`
- Avoid N+1 queries: fetch all related docs in one `get_list(filters={"name": ["in", ids]})` call, not in a loop
- Use `frappe.db.exists()` instead of `get_doc()` just to check existence

### Async for slow operations
- **Any operation > ~200ms must be enqueued** — use `frappe.enqueue_doc()` or `frappe.enqueue()`
- Preview image generation, image conversion (WebP), analytics ingestion — all run in background queues
- In tests, pass `now=frappe.flags.in_test` to run synchronously

### Page rendering
- `get_context()` runs on every public page request — keep it fast
- Set `context.no_cache = 1` **only** when genuinely required (dynamic routes, pages with data/block scripts)
- Static pages without scripts are served from Frappe's page cache — avoid breaking that cache unintentionally

Extend `FrappeTestCase` and use `frappe.get_test_records()` for fixtures.

```python
from frappe.tests.utils import FrappeTestCase

class TestBuilderPage(FrappeTestCase):
    def test_page_creation(self):
        page = frappe.get_doc({
            "doctype": "Builder Page",
            "page_name": "test-page",
            "route": "test-page",
        })
        page.insert()
        self.assertEqual(page.published, 0)
        page.delete()
```

Run: `bench --site builder.test run-tests --app builder --module builder.builder.doctype.builder_page.test_builder_page`

---

## Key Modules

| File | Purpose |
|------|---------|
| `builder/utils.py` | `Block` dataclass, `has_page_write` decorator, `safe_exec` wrapper, YAML helpers |
| `builder/api.py` | Asset upload, WebP conversion, page preview HTML |
| `builder/hooks.py` | Frappe integration (generators, jinja, scheduler) |
| `builder/ai_page_generator.py` | LLM prompts and litellm integration |
| `builder/builder_analytics.py` | DuckDB ingestion (scheduled) |
| `builder/builder/doctype/builder_page/builder_page.py` | Main page controller + renderer |
