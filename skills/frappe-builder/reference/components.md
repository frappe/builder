# Components

A `Builder Component` is one block tree (`block`, a JSON string holding a single root block) that pages embed as **instances**. `component_id` is also the doc name; `component_name` is the label. An optional `component_data_script` computes values per instance on the server.

Build any self-contained unit that could live on another page (header, footer, pricing card, tabs, a slider) as a component, with its behaviour inside it. Chrome that is shared across pages is always a component.

## Instances

```json
{"blockId": "x81k", "element": "div", "blockName": "Site Header",
 "extendedFromComponent": "<component id>",
 "props": {...per-instance prop entries...},
 "children": [
   {"blockId": "p2a9", "isChildOfComponent": "<component id>", "referenceBlockId": "<definition block id>", "children": [...]}
 ]}
```

- The instance's children are a **skeleton**: one ref per definition block, mirroring its nesting, each with a fresh `blockId`, `isChildOfComponent` and `referenceBlockId`. The server renders definition blocks through these refs, so an instance without a skeleton publishes empty. Copy `isRepeaterBlock: true` onto the ref of any definition repeater, or the canvas shows a single row.
- A ref may override `innerHTML`, styles (merged), `attributes`, `customAttributes`, `classes` (appended), `visibilityCondition`, bindings and `clientScript`. That is how a shared header gets this page's active nav item. Everything else comes from the definition.
- Editor-dropped instances also pin `componentVersion` (a snapshot of the component). A pinned instance keeps rendering that version until it is re-pinned; an unpinned one renders the live component.
- The simplest correct instance: pull a page that already embeds the component and copy that instance with fresh blockIds.

## Changing a component

- Update `block` with `frappectl doc update "Builder Component" <id> --input ...`. Keep existing blockIds: every page's skeleton points at them.
- Saving the component changes every unpinned instance on live pages at once; there is no draft. Then run `frappectl -s <p> method call builder.api.sync_component -F component_id=<id>`, which adds refs for new blocks and pins every instance to the new version, in both the draft and the live `blocks`, so pinned instances catch up too. Get the human's yes first, list the affected pages (`doc list "Builder Page" -f 'blocks like %<id>%'`), and keep the old `block` and `component_data_script` for rollback.
- Change shared chrome on the component itself, never page by page. An override on one page's ref is for that page only.

## Extracting a section into a component

Create the component with the section as its `block` root (the root sizes itself, and never carries `position`, `left` or `top`). Then replace the section on the page with an instance whose skeleton mirrors that root's children. Do the same on every other page that repeats the section.

## Props

Declare props on the definition root under `props.<name>`:

```json
{"label": "Heading", "isStandard": true, "isDynamic": false, "isPassedDown": true, "comesFrom": null, "value": null,
 "propOptions": {"type": "string", "isRequired": false, "options": {"defaultValue": "Questions"}, "dependencies": {}}}
```

- Types: `string`, `select` (`options.options` list), `number`, `boolean` (default `"true"`/`"false"` as strings), `array`, `object`, `color`, `image`.
- An instance entry repeats the whole declaration with `value` set. Array and object values are JSON **strings**; a real list crashes the canvas. The definition's `value` stays `null`.
- Name props in snake_case. The data script sees `props` as a dict with attribute access, so `props.items`, `props.keys` or `props.get` there is the dict method; read with `props.get("items")`, or avoid those names.
- Bind a mirroring block to it (`"comesFrom": "props"`, `"key": "title"`) rather than hardcoding the text. For a varying collection, a repeater over an array prop lets each page add or remove entries; baked child blocks don't.
- Records with several fields ride as delimited array rows (`"Quote | Name | Role"`). The data script splits them into `component.<list>`, and a repeater binds with `"comesFrom": "componentData"`.

## Data script and client script

- `component_data_script` gets `props` (resolved, typed) and fills `component`. It runs once per instance, as the visitor. Only `component.component_data` reaches the client script.
- A block's `clientScript: {"js": ..., "css": ...}` runs once per rendered instance. `js` is a function body with `this` = the instance element and `(component_data, props)` as arguments; `css` is scoped to that block. Select through `this.querySelector` and class hooks, set state from `props` before wiring listeners, and return a cleanup function (the editor re-runs scripts).
- In the editor, scripts run sandboxed: guard timers and listeners behind `typeof window !== "undefined"`, and write with `textContent`, `classList` or `replaceChildren` rather than `innerHTML`.
