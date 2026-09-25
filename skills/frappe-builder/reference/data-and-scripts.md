# Data, scripts and forms

## Page data script

`page_data_script` is restricted Python that runs on every render and fills `data`; blocks bind to its keys (see `blocks.md`).

```python
data.events = frappe.get_all("Event", filters={"event_type": "Public"}, fields=["name", "subject", "starts_on"], order_by="starts_on asc", limit=12)
for event in data.events:
	event.date_label = frappe.utils.format_date(event.starts_on, "d MMM")
```

- It runs as the visitor, usually Guest. `frappe.get_all` reads without permission checks, so filter to what is public. `frappe.get_list` raises PermissionError for guests, and `frappe.get_doc` hands back a Document, which can't be subscripted.
- Use `frappe.utils.parse_json`; `frappe.parse_json` is not exposed. Tuple unpacking fails under the restricted executor; index instead.
- `redirect("/path")` is available. Any exception, even a RestrictedPython compile error such as a name starting with `_`, fails the whole page with a 500, so guard lookups that can miss.
- Test by previewing the draft (`builder.api.get_page_preview_html`), which runs the script. `frappectl doctype show <DocType>` gives you the real field names first.

## Dynamic routes

A route with a parameter (`events/:event` or `events/<event>`) matches every value. The data script reads it as `frappe.form_dict.event`, loads that record, and handles a value that matches nothing. Put detail pages under their collection's route and link them from the collection's repeater (bind `href`).

## Client scripts

A `Builder Client Script` is a JS or CSS file the page links. It is created once and attached by name, so one script can serve many pages:

```sh
frappectl -s <p> doc create "Builder Client Script" --input script.json   # {"name": "Events Filter", "script_type": "JavaScript", "script": "..."}
frappectl -s <p> doc update "Builder Page" <page> --input links.json      # {"client_scripts": [{"builder_script": "Events Filter"}, ...]}
```

- The `client_scripts` list you send replaces the page's list, so include the scripts already attached.
- Give each script a descriptive `name`. JS and CSS are separate scripts, and JS never injects `<style>`.
- Scripts run at the end of `<body>`, so the page's elements already exist. `window.page_data` is empty. To hand server values to JS, bind them to a `data-*` attribute (a `type: "attribute"` binding), then read `element.dataset`.
- Toggle your own classes with `classList`. Assigning `className` removes the block's generated `fb-` class, and with it every style set on the block.
- Select elements by the classes you set on blocks.
- Published pages have no Frappe JS; call APIs with `fetch('/api/method/...')` and the `X-Frappe-CSRF-Token: frappe.csrf_token` header.
- Always save a script through `doc update`: saving regenerates the file the page links (`public_url`, with a `?v=` hash). If the live page still loads the old `?v=`, save the script once more.
- Behaviour that belongs to a reusable widget goes in a component's own `clientScript` instead; see `components.md`.

## Forms that save

Visitors are guests, so a form can't insert into a DocType directly. The safe chain is Frappe's Web Form, whose `accept` endpoint is guest-allowed, rate-limited and restricted to its fields:

1. A private custom DocType for the submissions (`custom: 1`, `naming_rule: "Random"`, permissions for System Manager only). Use Data, Small Text, Text, Int, Float, Check, Date or Datetime fields; store dropdown answers as Data, because option labels rarely match the submitted values. Field names avoid Frappe's reserved names (`name`, `owner`, `parent`, `idx`, ...).
2. A `Web Form` on it: `published: 1`, `login_required: 0`, `allow_multiple: 1`, with the same fields.
3. A client script on the page that collects the inputs and POSTs `{"web_form": "<web form name>", "data": {...}}` to `/api/method/frappe.website.doctype.web_form.web_form.accept`, then shows a confirmation.

Creating the DocType needs System Manager and the human's yes. Afterwards, tell them where submissions land: `/app/<doctype-slug>`. Style each input's focus state along with it.

## Site-wide code and settings

`Builder Settings` holds `style` and `script` (loaded on every Builder page), `head_html`/`body_html` (every page; a page's own `head_html`/`body_html` add to them), `home_page` (the route served at `/`), `favicon`, and `disable_auto_dark_mode`. Every change here reaches every page: ask first, and read the current value before you replace it.
