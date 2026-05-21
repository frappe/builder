---
description: "Use when writing, editing, or reviewing any scripting features: page data scripts, block data scripts, block client scripts, builder client scripts (shared JS/CSS), safe_exec, execute_script, scripting security, or the scripting UI dialogs. Covers all three layers of the Builder scripting system."
---

# Scripting System — Frappe Builder

Builder has **three independent scripting layers**. Each runs at a different time and in a different environment.

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Page Data Script        (Python, server, per-request)  │
│ Layer 2: Block Data Script       (Python, server, per-block)    │
│ Layer 3: Block Client Script     (JavaScript, browser, runtime) │
└─────────────────────────────────────────────────────────────────┘
```

Additionally: **Builder Client Scripts** are shared JS/CSS files attached to a page (like `<link>` / `<script>` tags).

---

## Layer 1 — Page Data Script

**When**: Runs once per HTTP request, before the block tree is rendered.
**Language**: Python (restricted sandbox via `safer_exec`).
**Where stored**: `BuilderPage.page_data_script` (Code field).
**Purpose**: Fetch data from Frappe DB or external APIs and inject into the Jinja template context for the entire page.

### Available globals in sandbox

```python
# Available in page_data_script:
data      # frappe._dict() — write page-level context here
page      # frappe._dict() — alternative namespace

frappe.db.get_all(doctype, ...)
frappe.db.get_list(doctype, ...)
frappe.db.count(doctype, filters)
frappe.db.exists(doctype, name)
frappe.db.get_single_value(doctype, field)
frappe.get_doc(doctype, name)           # returns as dict
frappe.get_cached_doc(doctype, name)    # returns as dict
frappe.form_dict                        # URL query params / form data
frappe.session                          # { user, sid, ... }
frappe._("string")                      # translation
frappe.make_get_request(url)            # external HTTP GET
args                                    # alias for frappe.form_dict
json                                    # json module
```

### Pattern

```python
# page_data_script — runs server-side for every page request
products = frappe.db.get_all(
    "Item",
    filters={"is_active": 1},
    fields=["item_name", "image", "standard_rate"],
    limit=10,
)
data.products = products
data.title = "Our Products"
```

Then in the block tree, `{{ products }}` and `{{ title }}` are available as Jinja variables.

### Security

- Runs inside `RestrictedPython` + `safer_exec` — a subset of Python
- `frappe.db` methods are wrapped to ignore permissions (`ignore_permissions=True`)
- No file system access, no `import`, no `exec/eval`
- Keep scripts focused on data fetching only — no business logic or mutations

---

## Layer 2 — Block Data Script

**When**: Evaluated at request time for each block that has one (lazy, per-block).
**Language**: Python (same sandbox as page data script).
**Where stored**: `Block.blockDataScript` (in the JSON block tree).
**Purpose**: Compute block-specific data (e.g., a hero block fetching its own content) without polluting the page context.

### How it works at render time

The renderer emits a Jinja expression that calls a custom filter:

```jinja2
{% with block = block | execute_script_and_combine('<escaped_script>', props, block_id) %}
  ... block HTML ...
{% endwith %}
```

`execute_script_and_combine` is a Jinja filter registered in `hooks.py` that runs the Python script in the sandbox and merges the result into the `block` dict.

### Available globals (same as page data script, plus)

```python
block     # frappe._dict() — current block's data dict; read previous values, write new ones
props     # dict — props passed down from parent blocks/components
```

### Pattern

```python
# blockDataScript — runs per block, per request
article = frappe.get_cached_doc("Blog Post", props.get("post_id"))
block.title = article["title"]
block.image = article["image"]
block.author = article["author"]
```

---

## Layer 3 — Block Client Script

**When**: Runs in the browser after the page loads (vanilla JavaScript).
**Language**: JavaScript (no bundler, no framework — plain ES6).
**Where stored**: `Block.blockClientScript` (in the JSON block tree).
**Purpose**: DOM interaction, animations, event listeners for a specific block instance.

### Execution context

Each block client script is wrapped in a named function and called with `this` pointing to the block's root DOM element:

```javascript
// Generated output (simplified):
function client_script_<blockId>(props, block_data) {
    // your script here — `this` is the block's DOM element
}
// Called per block instance:
client_script_<blockId>.call(
    document.querySelector('[data-block-uid="<unique_hash>"]'),
    {{ props | to_safe_json }},
    {{ block.block_data | to_safe_json }}
);
```

### Pattern

```javascript
// blockClientScript — runs in browser, `this` = block DOM element
const button = this.querySelector("button");
button.addEventListener("click", () => {
    this.classList.toggle("active");
});

// Access server-provided data via the second argument:
// function client_script_xxx(props, block_data) { ... }
console.log(props.variant);   // prop from parent
console.log(block_data.title); // data from blockDataScript
```

### Constraints

- No `import`, no `require` — this is inline JavaScript
- Script runs once per block instance (including inside loops/repeaters)
- `this` is always the block root element — use `this.querySelector()` not `document.querySelector()`
- The function definition is emitted **once** per unique block type; the call is emitted per instance

---

## Builder Client Scripts (Shared JS/CSS)

**When**: Injected as `<script src="...">` or `<link rel="stylesheet">` into the page `<head>`.
**Doctype**: `BuilderClientScript` — stores compiled JS or CSS with a `public_url`.
**Attached via**: `BuilderPage.client_scripts` (child table of links).
**Scope**: Entire page (all blocks share it).

Use for: shared utility functions, third-party libraries, global CSS variables.

```python
# set_style_and_script() in builder_page.py:
for script in client_scripts:
    script_doc = frappe.get_cached_doc("Builder Client Script", script.builder_script)
    if script_doc.script_type == "JavaScript":
        context.setdefault("scripts", []).append(script_doc.public_url)
    else:
        context.setdefault("styles", []).append(script_doc.public_url)
```

---

## Global Head/Body HTML

`BuilderSettings` and `BuilderPage` both have `head_html` and `body_html` fields. These are raw HTML snippets injected into every page (settings-level) or a specific page. They support Jinja templating with the page context.

```python
# Rendered as:
context._head_html = render_template(builder_settings.head_html + page.head_html, context)
context._body_html = render_template(builder_settings.body_html + page.body_html, context)
```

---

## `safer_exec` vs `execute_script`

| Function | Where | Restriction level |
|----------|-------|------------------|
| `safer_exec()` in `utils.py` | Used for page/block data scripts | RestrictedPython + custom `get_safer_globals()` |
| `execute_script()` in `utils.py` | Wrapper around `safer_exec` | Same — adds error wrapping and logging |
| Frappe's `safe_exec()` | Frappe core | Standard Frappe sandbox |

Always use `execute_script()` (not bare `exec` or `eval`) when running user-supplied Python in the backend. Never bypass the sandbox.

---

## Scripting Security Rules

- **Never use `exec()` or `eval()` directly** on user scripts — always route through `execute_script()`
- The sandbox blocks: `import`, file I/O, `os`, `subprocess`, network calls (except `frappe.make_get_request`)
- `frappe.db` methods in the sandbox have `ignore_permissions=True` — be aware that data is accessible regardless of user role; do not expose sensitive fields without explicit filtering
- Validate and sanitize any user-supplied values passed through `props` or `args` before using in DB queries (to prevent injection)
- Client scripts are injected as-is into the page — do not allow arbitrary user input to become part of a `blockClientScript`
