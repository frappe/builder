# Block JSON

`blocks` and `draft_blocks` hold a JSON array with one root block. `page.py pull` gives you that array pretty-printed; `push` stores it compact.

## Root

```json
{"blockId": "root", "blockName": "body", "element": "div", "originalElement": "body",
 "baseStyles": {"display": "flex", "flexDirection": "column", "alignItems": "center", "flexShrink": 0,
                "backgroundColor": "#f4efe6"},
 "children": [...sections...]}
```

`originalElement: "body"` is what makes the renderer inject page scripts and the CSRF token, so keep it. Give the root the page's background: it backs every gap. Each top-level section takes `width: "100%"` and does its own layout inside.

## Fields

| Field | Notes |
|---|---|
| `blockId` | Unique in the tree. For new blocks, any short random string. |
| `element` | The tag. `p` renders as `div` on the published page, so script selectors target classes, never tags. |
| `originalElement` | Rendered **instead of** `element` when set. Drop it when you change a block's element (except `body` and `__raw_html__`). |
| `blockName` | The layers-panel label. Name every block you add. |
| `baseStyles` / `tabletStyles` / `mobileStyles` | Desktop first. The tablet and mobile maps hold only the overrides. |
| `attributes` | `src`, `darkSrc`, `alt`, `href`, `title`, `value`, `type`, `placeholder`, `target`, `rel`. |
| `customAttributes` | Everything else: `id`, `data-*`, `aria-*`, `role`. |
| `classes` | Extra classes, your hooks for scripts and CSS. |
| `innerHTML` | Content of a text block; may hold inline HTML. |
| `children` | Child blocks. |

## Styles

- camelCase property names, CSS values as strings with units (`"padding": "24px"`). Keyword values stay in CSS form (`"justifyContent": "space-between"`).
- State styles are prefixed keys: `"hover:backgroundColor"`, `"focus:borderColor"`. A styled input pairs `"focus:outline": "none"` with a visible replacement.
- Keys are stored sorted, so their order in your JSON is lost. A shorthand that sorts after a longhand overrides it (`borderWidth` after `borderLeft`, `gap` after `columnGap`). Write longhands only, or order-independent values.
- Gradients go in `backgroundImage`, colours in `backgroundColor`. The editor canvas drops a `background` shorthand that holds `var()`, although the published page keeps it.
- `fontFamily` is one bare Google Fonts family name (`"Fraunces"`); the page loads it automatically. Use no quotes, no fallback stack and never `inherit`, which the font loader requests as a font called "inherit".
- `var(--token)` takes no fallback. The fallback goes stale when the token is edited.
- Anything `position: absolute`/`sticky`, sized in `vw`, or placed with grid areas ships its `mobileStyles` fallback in the same block.

## Text

Text shows in the canvas only on text elements: `span h1-h6 p b label a cite li strong em i blockquote summary button`. Text on a `div` is invisible in the editor, although the published page shows it. Every block is block-level, so a multi-colour sentence or highlighted code is **one** block whose `innerHTML` carries inline `<span style="color:...">` runs, never one block per word. Code goes in a `pre`.

## Images

`element: "img"`, `attributes.src` and `alt`, with `objectFit` and explicit dimensions or `aspectRatio`. A dark-mode image is `attributes.darkSrc` beside `src`; Builder swaps it in by itself. Upload local files with `frappectl file upload <path>`, and import remote images into the site with `frappectl method call builder.api.import_remote_assets -F 'urls:=["https://..."]'`, which returns old URL → site URL. Never hotlink.

## Icons and raw HTML

- Lucide icon: `element: "svg"`, `customAttributes: {"data-lucide": "arrow-right"}`, `innerHTML` = the icon's SVG from `https://unpkg.com/lucide-static/icons/<name>.svg` with the `class` attribute removed and `width`/`height` set to `100%`. `baseStyles`: `display: inline-flex, alignItems: center, justifyContent: center, lineHeight: 0, flexShrink: 0`, plus `width`, `height` and `color` (the stroke follows `color`).
- An embed, illustration or other raw markup: `element: "div"`, `originalElement: "__raw_html__"`, markup in `innerHTML`. Draw abstract art this way, never a real subject (product, food, person); use a photo for those.
- Code goes in client scripts (see `data-and-scripts.md`), not `script` or `style` blocks, which publish as raw tags outside the page's script list.

## Bindings

A binding pulls a value into a block at render time. `{{ x }}` typed into `innerHTML` runs as Jinja on the published page but shows raw in the editor, so bind instead.

```json
"dataKey": {"key": "title", "comesFrom": "dataScript", "type": "key", "property": "innerHTML"}
```

- `comesFrom`: `dataScript` (the page data script's `data.<key>`), `props` (a component prop), `componentData` (a component data script's `component.<key>`).
- `type`: `key` for a block field (`innerHTML`), `attribute` for `src`/`href`/`data-*` (`property` names it), `style` for a camelCase style.
- The primary binding sits in `dataKey`; further ones go in `dynamicValues` (a list of the same shape), one per property.
- A key is a bare dotted identifier (`title`, `event.city`). Formatting and conditions are computed in the data script and bound as a plain key.
- The block's authored value is the fallback when the key is missing, so give bound text real placeholder copy.

## Repeaters

`isRepeaterBlock: true`, `dataKey: {"key": "events", "comesFrom": "dataScript"}`, and exactly one child: the template, rendered once per record. Inside the template, bind the record's fields by bare name (`"key": "city"`).

## Visibility

`visibilityCondition: {"key": "has_discount", "comesFrom": "dataScript"}` removes the block from the published page when the value is falsy. The canvas only dims it.
