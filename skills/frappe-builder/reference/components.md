# Components

A `Builder Component` stores one block tree in `block` (a JSON string) and an optional `component_data_script`. Its doc name is its `component_id`. Pages embed it as an **instance**: a block with `extendedFromComponent` whose children are a **skeleton** of refs (`referenceBlockId` = a definition blockId, `isChildOfComponent` = the component id). The server renders the definition through the skeleton, so an instance without one renders empty, and definition blocks missing from it don't render.

An instance mirrors the definition. Its root is `{"blockId": <new>, "element": <root's element>, "blockName": <root's blockName>, "extendedFromComponent": <id>, "children": [...]}`, and each definition block below the root becomes a ref `{"blockId": <new>, "referenceBlockId": <its blockId>, "isChildOfComponent": <id>, "children": [<refs of its children>]}`, keeping `isRepeaterBlock`. A nested component's ref also keeps its `extendedFromComponent`, and its children mirror that component's own definition with that component's id. From a shell, `builder.py instance <id>` builds it.

`examples/tabs/` is a complete component (props, data script, repeaters, script with keyboard support, scoped CSS) that renders and behaves the same live and in the editor. Create a component as a `Builder Component` with `component_id`, `component_name`, `block` (`block.json` as a string) and `component_data_script`; from a shell, `builder.py create tabs --from <skill-dir>/examples/tabs --name Tabs`.

## When to make one

A component is a block tree that repeats, on one page or across pages, and changes in one place. A section used once stays plain blocks on the page, and a component's parts stay its own blocks unless they repeat elsewhere too. Reuse an existing component before creating one.

## Props

Each page edits an instance's blocks in place, in the editor or with overrides on its refs: text, images and alt text, links, styles, and hiding a block. So leave those blocks unbound in the definition, with real default content, instead of declaring a prop per field, even when one value fills several blocks. A prop is only for:

- what the editor can't edit on an instance, like the list a repeater renders,
- a value a client script or the data script needs.

A data script that only copies a value through, or single-value fallbacks for a list prop, doesn't make a prop needed.

Declared on the definition root under `props.<name>`, in the shape the editor writes:

```json
"title": {"label": "Title", "isStandard": true, "isDynamic": false, "isPassedDown": true, "comesFrom": null, "value": null,
          "propOptions": {"type": "string", "isRequired": false, "options": {"defaultValue": "Hello"}, "dependencies": {}}}
```

- Types: `string`, `select` (`options.options` list), `number`, `boolean` (`defaultValue` `"true"`/`"false"`), `array`, `object`, `color`, `image`.
- Keep `isPassedDown: true`: without it the definition's own children can't see the prop live, though the editor shows it.
- An instance sets props in its root's `props`: each entry is the whole declaration with `value` set, arrays and objects as JSON strings, booleans and numbers as themselves, anything else as a string. A bare `{"value": ...}` works in the editor and falls back to the static text live.
- A repeater over a prop needs an `array` (or `object`) prop; over any other type it fails the page.
- For records with several fields, take an array of delimited rows (`"Label | Body"`) and split them in the data script, as the tabs example does.

## Data script

`component_data_script` runs once per instance per render, with `props` (resolved values) and an empty `component` to fill. Bindings and repeaters read `component.<key>` (`comesFrom: "componentData"`); the client script receives only `component.component_data`. The same two-executor rules as page data scripts apply (`data-and-scripts.md`), and props is a dict with attribute access, so read list props with `props.get("items")`.

## Client script and scoped CSS

`clientScript: {"js": ..., "css": ...}` on a block runs once per rendered instance: `js` is the body of an async function with `this` = the block's element and `(component_data, props)` as arguments; it runs inline while the page parses, before page scripts. `css` is scoped to the block.

- Plain selectors match descendants; `&` or `:scope` is the block itself.
- Scope every query to `this`: several instances share one page.
- Props that contain `<` or `&` arrive HTML-escaped (`&lt;`, `&amp;`) in the script.
- `window.events.dispatch(name, data)` / `events.listen(name, callback)` connect components.

The editor runs the same script in a sandbox, re-running it when props change. There, `window`, `setTimeout`, `document.createElement`, `parentElement`, setting `innerHTML`, and click listeners all throw; keydown listeners, `textContent`, `classList`, `dataset`, `fetch` and `events` work. So: build structure with blocks and repeaters, paint every state from `props` first, then wire behaviour behind `const live = typeof window !== "undefined"`. A script on an `img` still gets the element as `this`, but its CSS scope is lost.

## Instances and overrides

A skeleton ref can override the definition block it points at, per page: styles merge per key, `classes` append, `attributes` merge, `innerHTML` replaces non-empty text (an empty string can't blank it), `display: none` hides it. An instance root's `clientScript: {"js": ""}` disables the definition's script live, not in the editor. Set an override on the ref whose `referenceBlockId` is the block, or on the instance root for the definition's root, and never on `blockId`, `referenceBlockId`, `isChildOfComponent`, `extendedFromComponent`, `children` or `props`. From a shell, `instance` writes them keyed by the definition's blockNames (blockIds when names repeat):

```sh
builder.py instance hero --overrides '{"title": {"innerHTML": "..."}, "image": {"attributes": {"src": "...", "alt": "..."}}, "video": {"baseStyles": {"display": "none"}}}'
```

- Blocks you add to a skeleton render too, until a sync drops them.
- A component nested in another: the outer definition's overrides of the inner component's blocks are not applied, and a prop set on the inner instance shows live but not in the editor. The inner script's `props` also receives an ancestor's value for a same-named prop, so give nested props distinct names.
- A component can bind page data (`comesFrom: "dataScript"`), but then it only works on that page.
- A deleted component's instances render nothing, without an error.

## Changing a component

1. Edit `block` and keep every existing blockId: instance skeletons point at them (`builder.py push` refuses dropped ids).
2. Save it: live at once for unpinned instances (pages written over the API, which carry no `componentVersion`).
3. `builder.api.sync_component` with `component_id`: pins every instance (pinned or not) to the new version, adds refs for new blocks, drops blocks the definition doesn't have, keeps overrides, and rewrites both `draft_blocks` and the live `blocks` of every embedding page. Editor-dropped instances carry a `componentVersion` pin and only change after this.

First find the pages that embed it: Builder Pages whose `blocks` or `draft_blocks` contain its id (`builder.py usage <id>`). Wait about 15 seconds after publishing a page before saving a component it uses; see `live-and-cached.md`.
