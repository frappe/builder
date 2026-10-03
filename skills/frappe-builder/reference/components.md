# Components

A `Builder Component` stores one block tree in `block` (a JSON string) and an optional `component_data_script`. Its doc name is its `component_id`. Pages embed it as an **instance**: a block with `extendedFromComponent` whose children are a **skeleton** of refs (`referenceBlockId` = a definition blockId, `isChildOfComponent` = the component id). The server renders the definition through the skeleton, so an instance without one renders empty, and definition blocks missing from it don't render. Get a correct instance from `builder.py instance <id> --props '{...}'`.

`examples/tabs/` is a complete component (props, data script, repeaters, script with keyboard support, scoped CSS) that renders and behaves the same live and in the editor: `builder.py create tabs --from <skill-dir>/examples/tabs --name Tabs`.

## Props

Declared on the definition root under `props.<name>`, in the shape the editor writes:

```json
"title": {"label": "Title", "isStandard": true, "isDynamic": false, "isPassedDown": true, "comesFrom": null, "value": null,
          "propOptions": {"type": "string", "isRequired": false, "options": {"defaultValue": "Hello"}, "dependencies": {}}}
```

- Types: `string`, `select` (`options.options` list), `number`, `boolean` (`defaultValue` `"true"`/`"false"`), `array`, `object`, `color`, `image`.
- Keep `isPassedDown: true`: without it the definition's own children can't see the prop live, though the editor shows it.
- An instance entry is the whole declaration with `value` set (`instance` builds it). A bare `{"value": ...}` works in the editor and falls back to the static text live.
- Number props render live as floats (`29.0`); format them in the data script if they are shown.
- A repeater over a prop needs an `array` (or `object`) prop; over any other type it fails the page.
- For records with several fields, take an array of delimited rows (`"Label | Body"`) and split them in the data script, as the tabs example does.

## Data script

`component_data_script` runs once per instance per render, with `props` (resolved values) and an empty `component` to fill. Bindings and repeaters read `component.<key>` (`comesFrom: "componentData"`); the client script receives only `component.component_data`. The same two-executor rules as page data scripts apply (`data-and-scripts.md`), and props is a dict with attribute access, so read list props with `props.get("items")`.

A page whose data comes only from component data scripts is still HTML-cached for 30 minutes (`live-and-cached.md`).

## Client script and scoped CSS

`clientScript: {"js": ..., "css": ...}` on a block runs once per rendered instance: `js` is the body of an async function with `this` = the block's element and `(component_data, props)` as arguments; it runs inline while the page parses, before page scripts. `css` is scoped to the block.

- Style the root with `&`, not `:scope` (the editor ignores `:scope`). Plain selectors match descendants.
- Scope every query to `this`: several instances share one page.
- Props that contain `<` or `&` arrive HTML-escaped (`&lt;`, `&amp;`) in the script.
- `window.events.dispatch(name, data)` / `events.listen(name, callback)` connect components.

The editor runs the same script in a sandbox, re-running it when props change. There, `window`, `setTimeout`, `document.createElement`, `parentElement`, setting `innerHTML`, and click listeners all throw; keydown listeners, `textContent`, `classList`, `dataset`, `fetch` and `events` work. So: build structure with blocks and repeaters, paint every state from `props` first, then wire behaviour behind `const live = typeof window !== "undefined"`. A script on an `img` still gets the element as `this`, but its CSS scope is lost.

## Instances and overrides

A skeleton ref can override the definition block it points at, per page: styles merge per key, `classes` append, `attributes` merge, `innerHTML` replaces non-empty text (an empty string can't blank it), `display: none` hides it. An instance root's `clientScript: {"js": ""}` disables the definition's script live, not in the editor.

- Blocks you add to a skeleton render too, until a sync drops them.
- A component nested in another: the outer definition's overrides of the inner component's blocks are not applied, and a prop set on the inner instance shows live but not in the editor. The inner script's `props` also receives an ancestor's value for a same-named prop, so give nested props distinct names.
- A component can bind page data (`comesFrom: "dataScript"`), but then it only works on that page.
- A deleted component's instances render nothing, without an error.

## Changing a component

1. `pull component/<id>`, edit `block.json`, keep every existing blockId (push refuses dropped ids: instance skeletons point at them).
2. `push`: live at once for unpinned instances (pages written over the API, which carry no `componentVersion`).
3. `sync <id>`: pins every instance (pinned or not) to the new version, adds refs for new blocks, drops blocks the definition doesn't have, keeps overrides, and rewrites both `draft_blocks` and the live `blocks` of every embedding page. Editor-dropped instances carry a `componentVersion` pin and only change after this.

Use `usage <id>` first, and wait about 15 seconds after publishing a page before saving a component it uses; see `live-and-cached.md`.
