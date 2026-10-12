# Block JSON

`blocks` and `draft_blocks` hold a JSON array with one root block.

```json
{"blockId": "root", "blockName": "body", "element": "div", "originalElement": "body",
 "baseStyles": {"display": "flex", "flexDirection": "column", "alignItems": "center"}, "children": []}
```

`originalElement: "body"` is load-bearing: without it the page silently drops its JS client scripts, `window.page_data`, the CSRF token and `body_html`.

## Fields

- `originalElement` renders instead of `element`; change both or drop it.
- `p` renders as `div`, and each block's `fb-` class changes on every render, so scripts and CSS select classes you set in `classes`.
- `attributes` holds `src`, `darkSrc`, `alt`, `href`, `target`, `rel`, `placeholder`, `type`, `value`, `title`; `customAttributes` everything else (`id`, `data-*`, `aria-*`, `role`). `darkSrc` works only in `attributes`, and wraps the image in `<picture>`.
- Text in `innerHTML` shows in the editor only on `span h1-h6 p b label a cite li strong em i blockquote summary button`; on a `div` it renders live but is invisible in the canvas.
- Raw HTML (`element: "div"`, `originalElement: "__raw_html__"`, markup in `innerHTML`) is for SVG, iframes and embeds: its text can't be edited in the editor, and its `<script>` never runs there.
- Images: `frappectl file upload <path>`, or `method call builder.api.import_remote_assets -F 'urls:=["https://..."]'` to copy remote images into the site (returns old URL -> new URL).

## Styles

- Values are CSS strings with units: a bare number is emitted as-is (`width: 100` does nothing).
- Breakpoints: `tabletStyles` apply at 1023px and below, `mobileStyles` at 576px and below. The editor frames are 1400, 800 and 420 wide.
- States are prefixed keys with one colon: `hover:color`, `focus:borderColor`, `before:content` (quote the value: `"'x'"`). `::before` doesn't work.
- Unbalanced parentheses in a value get escaped and the rule breaks.
- `fontFamily` is one bare Google Fonts family (`"Fraunces"`); it loads automatically. A stack (`"Inter, sans-serif"`) or `inherit` is mangled into a bad font request.
- `background` with a `var()` works live but the editor canvas drops it; use `backgroundColor`/`backgroundImage`.
- Sync and snapshot restore sort style keys, so a shorthand and its own longhand (`borderWidth` with `borderLeft`) can swap order: use longhands.

## Tokens

A `Builder Token` is referenced as `var(--<doc name>)`; its `token_name` is only a label and resolves to nothing. Create one with an explicit `name` to know its handle: `{"name": "acme-ink", "token_name": "Ink", "type": "Color", "value": "#1d1b16", "dark_value": "#f4efe6"}`. `dark_value` applies when the visitor's system is in dark mode.

## Bindings

```json
"dataKey": {"key": "title", "comesFrom": "dataScript", "type": "key", "property": "innerHTML"}
```

- `comesFrom`: `dataScript` (page data), `props` or `componentData` (inside components). `type`: `key` for `innerHTML`, `attribute` for `href`/`src`/`data-*`, `style` for a CSS property. Further bindings go in `dynamicValues`, same shape.
- Keys are bare dotted paths. A top-level `post.title` 500s the page when `post` is missing; set it to `{}` in the data script. No concatenation: compute values in the data script.
- Fallbacks: text bindings show `0` and `""` but fall back to the block's own text on `None`; attribute and style bindings fall back on any falsy value.
- A style binding is inline, so it beats `tabletStyles`/`mobileStyles`.

## Repeaters

`isRepeaterBlock: true`, `dataKey: {"key": "events", "comesFrom": "dataScript"}`, and one child template; extra children are dropped.

- The source must be a list of dicts. A dict or a list of strings renders in the editor but 500s live.
- Inside, keys are relative to the item (`"key": "city"`). A nested repeater binds its own list key. Page-level keys are out of reach inside a repeater; copy what the item needs onto it.

## Visibility

`visibilityCondition: {"key": "has_events", "comesFrom": "dataScript"}` removes the block live when falsy.

- Live, the key may be an expression with `==`, `!=`, `and`, `or`, `not`; `<` and `>` fail the page. The canvas only tests truthiness, so prefer a boolean computed in the data script.
- A condition on a repeater's direct child is ignored; put it on a block inside the template.
