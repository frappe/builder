# Data, scripts and forms

## Page data script

`page_data_script` runs on every render and fills `data`; blocks bind to its keys. It has no draft.

```python
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
events = frappe.db.get_all("Event", filters={"event_type": "Public"}, fields=["name", "subject", "starts_on"], order_by="starts_on asc", limit=12)
for event in events:
	day = str(event["starts_on"])[:10]
	event["date_label"] = day[8:10] + " " + MONTHS[int(day[5:7]) - 1]
	event["url"] = "/events/" + event["name"]
data.events = events
data.has_events = len(events) > 0
```

Sites with server scripts enabled run it with Frappe's safe API; sites without (common on hosted sites) with a smaller one. Write for both:

| Works in both | Only with server scripts on |
|---|---|
| `frappe.db.get_all(dt, filters=, fields=, order_by=, limit=)` | `frappe.get_all`, `frappe.get_list` |
| `frappe.db.count`, `frappe.db.exists`, `frappe.db.get_single_value` | `frappe.db.get_value`, `frappe.db.sql` |
| `frappe.get_doc(dt, name).get("field")` | `doc["field"]`, Document methods |
| `json`, `frappe.form_dict`, `frappe.session.user`, `def`, `lambda`, comprehensions, `try` | `frappe.utils.*`, `frappe.throw`, exception classes |

In both:
- It runs as the visitor, usually Guest. `frappe.db.get_all` skips permission checks, so filter to public records; `frappe.db.get_list` raises for Guests.
- No imports, no tuple unpacking (`a, b = x`), no names starting with `_` (so no `frappe._`), no `.strftime()`, no SQL functions in `fields`.
- A `def` can't see the script's top-level names; pass them in.
- Any exception fails the page. `redirect("/path")` returns a 302.

`data` merges into the page's template context: `data.style` wipes every block style, `data.preview` drops the token stylesheet; name keys after your content. `data.title` sets `<title>`.

`window.page_data` holds only `data.page_data`, and a date or Decimal inside it fails the page (convert with `str()`). For a single value, bind it to a `data-*` attribute and read `element.dataset`.

## Dynamic routes

A route like `events/:event` matches every value; the script reads `frappe.form_dict.event`, which also beats a query parameter of the same name.

- A static route beats a dynamic one; of two dynamic routes that match, the last published wins.
- Nothing 404s on its own: an unknown value renders with empty bindings. Check the record and `redirect("/404")`, or show an empty state. (`frappe.get_doc` on a missing name gives Guests a 403; `raise frappe.PageDoesNotExistError()` shows the not-found page with status 200.)
- `canonical_url` is rendered as Jinja: `https://example.com/events/{{ frappe.form_dict.event }}`.
- The draft preview takes route values as query parameters, except `page`, which it uses itself.

## Client scripts

A `Builder Client Script` (`script_type` `JavaScript` or `CSS`) is a file pages link by name; one script can serve many pages.

```sh
frappectl -s <p> doc create "Builder Client Script" --input script.json   # {"name": "Events Filter", "script_type": "JavaScript", "script": "..."}
frappectl -s <p> doc update "Builder Page" <page> --input links.json      # {"client_scripts": [{"builder_script": "Events Filter"}]}
```

- The `client_scripts` list you send replaces the page's list.
- Order live: component scripts run inline as their blocks parse; then the Builder Settings script; then page JS in list order, with the whole DOM present. CSS: block styles, then the Builder Settings style, then page CSS, which wins at equal specificity.
- Toggle classes with `classList`: assigning `className` drops the block's `fb-` class and all its styles.
- Published pages have no Frappe JS: `fetch('/api/method/...')` with the `X-Frappe-CSRF-Token: frappe.csrf_token` header.
- Page and site-wide scripts don't run in the editor canvas.

## Forms that save

Guests can't insert into a DocType directly; a Web Form's `accept` endpoint can:

1. A custom DocType for submissions (`custom: 1`, `naming_rule: "Random"`, System Manager permissions only). Store dropdown answers as Data.
2. A `Web Form` on it: `title`, `published: 1`, `login_required: 0`, `allow_multiple: 1`, the same fields. It also serves its own page at its route.
3. Page JS that POSTs `{"web_form": "<name>", "data": {...}}` with the CSRF header to `/api/method/frappe.website.doctype.web_form.web_form.accept`.

Submissions land at `/app/<doctype-slug>`.

## Site-wide

`Builder Settings` holds `style` and `script` (every Builder page), `head_html`/`body_html` (every page) and `home_page` (the route served at `/`).
