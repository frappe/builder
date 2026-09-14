# Create Builder Extensions

Use this guide when a user asks for a Builder extension or a Builder component.

This guide describes the current extension API and its Builder Hub package contract.

## Extension model

A Builder extension is a JavaScript module with a `manifest.json` file.

Builder runs each extension inside sandboxed iframes. The sandbox is `allow-scripts allow-forms`. It does not permit same-origin access, so each frame runs at an opaque origin.

The extension cannot import Builder stores or access the editor DOM. It calls Builder through `frappe-builder-extension-sdk`.

Builder transfers a `MessagePort` to each frame. The SDK uses this port for requests, responses, events, and action calls.

Builder starts one hidden `main` frame for each enabled extension. Builder opens other frames only when their surfaces need them.

An extension can use these frames:

| Slot | Purpose | How to declare it |
|---|---|---|
| `main` | Startup work and long-lived subscriptions | `builder.main(handler)` |
| `panel` | Content for one left panel tab | `builder.leftPanel.register({ component })` |
| `settings` | Content for one global settings page | `builder.settings.registerItem({ component })` |
| `dialog` | Content for a modal dialog | `builder.dialog.register({ component })` |
| `popover` | Content for a draggable popover | `builder.popover.register({ component })` |

Each frame imports the same extension entry. The SDK runs only the slot that Builder names during the handshake.

The extension build must use one SDK module instance. The Vite plugin keeps the SDK external for this reason.

## Choose the smallest surface

Builder provides three UI levels. Choose the smallest level that can meet the request.

| Level | Builder capability | Use it for |
|---|---|---|
| Host-rendered item | Toolbar buttons and context menu rows | A small command with standard Builder UI |
| Host-rendered controls | Property panel sections | Values that edit a selected block or call an action |
| Extension frame | Left panel, settings, dialog, or popover | Custom Vue UI or a complex workflow |

Prefer host-rendered items for simple commands. They use Builder components and match the editor UI.

Use a frame when the feature needs custom content. The extension owns all content inside its frame.

## Project structure

Use this minimum structure:

```text
my-extension/
├── manifest.json
├── README.md
├── LICENSE
├── package.json
├── vite.config.js
└── src/
    ├── main.ts
    ├── icon.svg
    ├── panel/
    │   ├── Panel.vue
    │   └── index.ts
    └── actions.ts
```

Add `dialog`, `popover`, or `settings` folders only when the request needs those slots.

Use these minimum package scripts:

```json
{
  "name": "@acme/builder-image-tools",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  }
}
```

## Manifest

Put `manifest.json` beside `vite.config.js`.

```json
{
  "v": 1,
  "name": "acme/image-tools",
  "label": "Image Tools",
  "description": "Edit and optimize images.",
  "version": "1.0.0",
  "entry": "main.js",
  "icon": "icon.svg",
  "capabilities": ["context.read", "block.read", "block.update"]
}
```

Use `publisher/name` for `name`. Use lowercase letters, digits, and hyphens in each part.

`description` is required and can contain up to 240 plain text characters. Builder shows it below
the label in the Extensions panel.

The `version` value must be SemVer without a `v` prefix. The `entry` value must be `main.js`.
Version 1 rejects unknown manifest fields.

The `icon` value is optional. Builder shows it beside the extension in the Extensions panel. Follow
these rules:

- Name one SVG file, with no folder in front of it.
- Put the file beside the entry, in `src/`.
- Draw it square. Builder draws it in a box of 16 by 16 pixels, and a wider file gets empty space
  above and below.
- Give every shape its own color. Builder draws the file in an `<img>` element, so the file cannot
  read the editor theme. Pick colors that stay readable on a light and a dark background.

Builder draws its own plug glyph for an extension that ships no icon.

Request only the capabilities that the extension uses. Builder rejects a protected method without its capability.

| Capability | SDK methods or behavior |
|---|---|
| `context.read` | `context.get`, `context.subscribe`, and `useBuilderContext` |
| `block.read` | `block.get` |
| `block.update` | `block.update` and bound property controls |
| `block.insert` | `block.insert` |
| `page.read` | `page.getBlocks` |
| `page.write` | `page.attachScript`, `page.detachScript`, `page.listScripts` |
| `token.write` | `tokens.set`, `tokens.unset` |
| `ui.dialog` | `ui.openDialog`, `ui.closeDialog` |
| `ui.popover` | `ui.openPopover`, `ui.closePopover` |
| `data.access` | Every `data.*` method, including `requestAccess` |
| `schema.write` | Every `schema.*` method |

Surface registration, actions, extension state, `ui.toast`, and `host.info` need no capability.

Builder rejects page writes in read-only mode. This rule covers `block.update`, `block.insert`, `page.write`, and token writes. It does not cover `data.*` or `schema.*`, which write to the site and not to the page.

A capability grants the right to ask. For `data.*`, the user must also grant access to each doctype. Read [Site data](#site-data).

## Package and build configuration

Install the SDK, Vite, and the selected UI framework.

```sh
npm install --save-dev frappe-builder-extension-sdk vite typescript
npm install vue
npm install --save-dev @vitejs/plugin-vue
```

Use the SDK Vite plugin.

```js
import vue from "@vitejs/plugin-vue";
import builderExtension from "frappe-builder-extension-sdk/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    vue(),
    builderExtension({ builderUrl: "http://builder.localhost:8080" }),
  ],
});
```

Set `builderUrl` to the Builder editor origin. A different origin creates a second SDK instance and breaks the channel.

The plugin finds `src/main.ts` or `src/main.js`. It writes the production entry as `dist/main.js`.

The plugin copies `manifest.json` into `dist`, and the icon the manifest names with it. It also puts
generated CSS into the entry module.

Dynamic imports stay as relative chunks. Do not change the relative Vite base.

## Protocol and errors

The SDK remains on `0.x` while its API stabilizes. Its package version is
separate from the extension protocol in `manifest.v`. Use `builder.host.info()`
to read the active Builder version and protocol.

Most SDK methods return a promise. Catch a rejection when the feature needs recovery or user feedback.

The error object can include one of these codes:

| Code | Meaning |
|---|---|
| `unknown_method` | This Builder version does not provide the method |
| `capability_required` | The manifest did not grant the required capability |
| `read_only` | The method would write while Builder is read-only |
| `invalid_params` | The call sent an invalid value or shape |
| `unknown_rule_key` | A `showWhen` or `enableWhen` rule used a key Builder does not know |
| `unknown_item` | The named surface, action, or frame does not exist |
| `already_registered` | The extension already registered a panel, settings page, dialog, or popover |
| `unknown_block` | The active canvas does not contain the block ID |
| `no_canvas` | Builder has no active canvas |
| `grant_required` | The access is not allowed. Call `data.requestAccess`, then check the answer for `"denied"` |
| `refused` | The user answered no to a schema dialog |
| `server_error` | The site rejected the data or schema call |
| `rate_limited` | The extension exceeded its request budget |
| `state_too_large` | The extension state exceeded 100 kB |
| `storage_full` | The browser could not store extension state |

A declaration handles `unknown_method` itself. It logs a warning and skips only that surface.

Other errors reject the call. Builder validates all parameters inside the host.

## Entry module rules

Put registrations at module scope. Every frame must read the same declarations.

Put startup work inside `builder.main`. Only the hidden main frame runs that handler.

Give the `action` field a function. The SDK holds the function and sends only its name.

```ts
import builder from "frappe-builder-extension-sdk";

builder.toolbar.register({
  name: "mark-selected",
  region: "right",
  icon: "lucide-check",
  tooltip: "Mark selected block",
  action: async () => {
    const context = await builder.context.get();
    const blockId = context.selection.blockId as string | undefined;
    if (!blockId) return;

    await builder.block.update(blockId, {
      attributes: { "data-marked": "true" },
    });
  },
  showWhen: { count: 1 },
  enableWhen: { readOnly: false },
});

builder.main(async () => {
  const host = await builder.host.info();
  console.info(`Builder ${host.version}, protocol ${host.protocol}`);
});
```

Do not put `toolbar.register` inside `builder.main`. A visual frame also needs the action and slot declarations.

The SDK sends declarations to Builder only from the main frame. Other frames keep local action handlers and slot loaders.

## Actions

An action keeps its function inside the extension frame. A function cannot cross the port, so Builder stores only a name.

The `action` field of a toolbar item, a context menu row, and a property control takes a function. The SDK holds the function under the item's own name. A control is held under `<section>.<control>`.

```ts
builder.contextMenu.register({
  name: "inspect-block",
  label: "Inspect block",
  action: async (actionContext) => {
    const blockId = actionContext.blockId as string;
    console.log(await builder.block.get(blockId));
  },
});
```

Keep the function in a separate file when it grows.

```ts
import { inspectBlock } from "./actions";

builder.contextMenu.register({ name: "inspect-block", label: "Inspect block", action: inspectBlock });
```

The `action` field also takes a string. Use a string to name an action that `builder.actions.register` holds. A frame other than the main frame must use a string, because only the main frame holds handlers.

```ts
builder.actions.register("inspect-block", async (actionContext) => {
  const blockId = actionContext.blockId as string;
  console.log(await builder.block.get(blockId));
});
```

Toolbar buttons call actions without a context object. Context menu actions receive `blockId` and `fromLayersPanel`.

Property controls receive `name`, `blockId`, and `value`. The extension can also call `builder.actions.run(name, context)`.

Action names belong to one extension. Builder cannot call an action from another extension.

## Surface API

### Toolbar

Use `builder.toolbar.register` for a standard toolbar button.

```ts
builder.toolbar.register({
  name: "open-picker",
  region: "right",
  icon: "lucide-image",
  label: "Pick image",
  tooltip: "Open image picker",
  action: "open-picker",
  badge: 3,
  before: "preview",
  showWhen: { count: 1, isImage: true },
  enableWhen: { readOnly: false },
});
```

The `region` value must be `left`, `center`, or `right`. The `action` field is optional. It takes a function or an action name.

Use `toolbar.update(name, patch)` for `visible`, `enabled`, `label`, `icon`, `tooltip`, or `badge`.

Use `toolbar.unregister(name)` to remove the button.

### Context menu

Use `builder.contextMenu.register` for the canvas menu, layers menu, or both menus.

```ts
builder.contextMenu.register({
  name: "wrap-block",
  label: "Wrap block",
  action: "wrap-block",
  menu: "both",
  showWhen: { isRoot: false },
  enableWhen: { readOnly: false },
});
```

The `action` field is required here. It takes a function or an action name.

The `menu` value can be `canvas`, `layers`, or `both`. Builder uses `both` when the field is absent.

Builder tests conditions against the clicked block. This behavior differs from other surfaces, which use the current selection.

Use `contextMenu.update` or `contextMenu.unregister` after registration.

### Property section

Use `builder.properties.registerSection` for controls in the right panel.

```ts
builder.properties.registerSection({
  name: "image-options",
  label: "Image options",
  showWhen: { count: 1, isImage: true },
  controls: [
    {
      name: "alt",
      control: "text",
      label: "Alt text",
      placeholder: "Describe the image",
      bind: { attribute: "alt" },
    },
    {
      name: "opacity",
      control: "range",
      label: "Opacity",
      bind: { style: "opacity" },
      min: 0,
      max: 1,
      step: 0.1,
    },
  ],
});
```

Available controls are `text`, `number`, `select`, `toggle`, `color`, and `range`.

A bound control writes an attribute or a style. Bound controls require the `block.update` capability.

An unbound control needs an `action`. It sends its value to the action when the value changes. Builder rejects a control that has neither `bind` nor `action`.

A bound control can also have an action. Builder writes the value, then calls the action.

Use `value` for an unbound control that shows the extension's own value. Use `placeholder` for a hint inside the control.

Use `options` for `select` and `toggle`. A toggle option can carry an `icon`. Use `min`, `max`, and `step` for numeric controls.

Give a control its own `showWhen` to hide that control while the section stays.

Use `properties.setControls(name, controls)` to replace the complete control list.

Use `properties.update(name, patch)` to change the section label or visibility. Use `properties.unregisterSection(name)` to remove it.

### Left panel

An extension can register one left panel tab. Builder mounts its frame when the user first opens the tab.

```ts
builder.leftPanel.register({
  name: "assets",
  label: "Assets",
  icon: "lucide-images",
  component: () => import("./Panel.vue"),
  showWhen: { readOnly: false },
});
```

Builder keeps the frame alive after its first mount. Component state remains until Builder removes the frame.

Use `leftPanel.update` to change the label, icon, or visibility. Use `leftPanel.unregister` to remove the tab.

### Settings

An extension can register one settings page. Builder places it in the `Global` settings group. There is no way to add a group.

```ts
builder.settings.registerItem({
  name: "preferences",
  label: "Image tools",
  title: "Image tool preferences",
  icon: "lucide-settings",
  component: () => import("./Settings.vue"),
});
```

The `title` value defaults to `label` when the registration omits it.

Use `settings.update` to change the label, title, icon, or visibility. Use `settings.unregisterItem` to remove the page.

### Dialog and popover

Declare each slot once at module scope.

```ts
builder.dialog.register({ component: () => import("./Dialog.vue") });
builder.popover.register({ component: () => import("./Popover.vue") });
```

Open a slot from an action or another frame.

```ts
const result = await builder.ui.openDialog({
  title: "Choose an image",
  props: { accept: ["image/png", "image/jpeg"] },
});
```

The slot reads its input with `builder.ui.props()`. It returns a result with `builder.ui.closeDialog(result)`.

Use `openPopover`, `closePopover`, and the `ui.popover` capability for a popover.

Give a popover a start size with `width` and `height`, in pixels. Builder uses its own
size for a field you omit. The user can always drag the corner to resize it.

```ts
await builder.ui.openPopover({ title: "Palette", width: 333, height: 591 });
```

A dialog has no size. Builder draws it at one size for every extension.

Builder permits one open dialog and one open popover per extension.

### The Open button

The extension details pane draws an `Open` button. Say what it opens with
`builder.open.register`. An extension that registers no target gets no button.

```ts
builder.open.register({ kind: "popover", width: 333, height: 591 });
builder.open.register({ kind: "dialog", title: "Choose an icon" });
builder.open.register({ kind: "leftPanel", name: "icons" });
```

Declare it at module scope, beside the slot or the tab it opens. A `leftPanel` target
names a tab this extension registered. Builder opens the target itself, so the
extension needs no capability for it.

Use `builder.open.unregister()` to take the button back.

### Toast

Use `builder.ui.toast` for a short message outside the frame. It needs no capability.

```ts
builder.ui.toast("Image replaced", { type: "success" });
```

The `type` value can be `success`, `error`, `warning`, or `info`. Builder shows its standard message toast when the call omits the type.

## Conditions

Use `showWhen` to control visibility. Use `enableWhen` to control actions on toolbar and context menu items.

Builder supports these condition keys:

| Key | Type |
|---|---|
| `isRoot` | `boolean` |
| `isText` | `boolean` |
| `isImage` | `boolean` |
| `isHTML` | `boolean` |
| `isContainer` | `boolean` |
| `count` | `number` |
| `breakpoint` | `desktop`, `tablet`, or `mobile` |
| `readOnly` | `boolean` |

All fields must match. Builder rejects unknown condition keys during registration with `unknown_rule_key`.

A block-specific value is absent when the user selects zero or multiple blocks. A related condition then fails.

Use `showWhen` before a context subscription. Conditions run inside Builder and require no messages.

Use `before` or `after` to place a surface near an existing registry item. Builder keeps the surface position during updates.

## Read editor data

Use `builder.context.get()` for one editor snapshot.

The snapshot contains `selection`, `breakpoint`, `editingMode`, `readOnly`, `isAIEnabled`, `page`, and `site`.

The selection always contains `count` and `blockIds`. It contains one block's facts only when exactly one block is selected.

One block can report these facts:

```text
blockId, element, isRoot, isText, isImage, isHTML, isSVG,
isLink, isContainer, isVideo, isInput, isRepeater,
isComponent, isChildOfComponent
```

Use `builder.context.subscribe(fields, handler)` for changes. The host sends only the requested fields.

The host limits context events to one batch per 100 milliseconds. The returned function removes the local listener.

The host keeps the subscribed field set until extension teardown. The wire API has no unsubscribe method.

For Vue, use `useBuilderContext(fields)` from `frappe-builder-extension-sdk/vue`. It returns a reactive snapshot.

## Read and change blocks

Use `builder.block.get(blockId)` to get one block and its subtree. The result is a plain object without parent links.

Use `builder.page.getBlocks()` to get all root blocks. Walk each node's `children` field to inspect the tree.

During component editing, `page.getBlocks()` returns the component fragment. Check `context.editingMode` before processing the tree.

Use `builder.block.update(blockId, patch)` to change a block.

```ts
await builder.block.update(blockId, {
  attributes: { title: "Example", hidden: null },
  styles: { color: "red", padding: null },
  classes: ["card", "card-featured"],
  innerHTML: "Example text",
  breakpoint: "desktop",
});
```

An attribute value of `null` removes the attribute. A style value of `null` or an empty string removes the style.

The `breakpoint` field applies only to styles. Builder uses the active breakpoint when this field is absent.

The `classes` field replaces the complete class list. The `innerHTML` field replaces the block content.

Builder rejects a patch that changes nothing.

Use `builder.block.insert(parentId, block, index)` to add a block tree. Builder appends the tree when the call omits `index`.

```ts
const { blockId, keys } = await builder.block.insert(parentId, {
  element: "div",
  classes: ["feature-card"],
  styles: { padding: "16px" },
  children: [
    { element: "h3", innerHTML: "New feature" },
    { element: "button", key: "cta", innerHTML: "Read more" },
  ],
});

await builder.block.update(keys.cta, { attributes: { type: "button" } });
```

A block carries its own `children`, so one call draws a whole card and makes one undo step.

Give a node a `key` to find it again. The result maps each `key` to the block it became. Two nodes cannot share a key.

A tree can hold 200 blocks and go 20 levels deep. Builder checks the whole tree before it adds anything, so a refusal leaves the page unchanged.

Builder does not select the new blocks. Each update or insert uses Builder's normal undo history.

## Page client scripts

A block change alone cannot make a published page do anything. Use `builder.page.attachScript` to put
JavaScript or CSS on the page the user has open.

```ts
await builder.page.attachScript({ type: "CSS", script: "@keyframes fade-up { ... }" });
await builder.page.attachScript({ type: "JavaScript", script: "document.querySelectorAll(...)" });
```

Read these rules before you use it:

- The script runs on the published page. It does not run in the editor canvas. The editor shows what
  a block is set to, and the page shows what it does.
- One JavaScript script and one CSS script per extension per page. A second call of the same type
  replaces the script, so send the whole file every time.
- The first script of a type asks the user, and the prompt names the page. A later call to replace
  the same script does not ask.
- Builder rejects the call in read-only mode.

Use `builder.page.listScripts()` to read the scripts this extension owns on the open page. Call it
once at startup, and keep the answer, so a control that fires often does not attach on every change.

Use `builder.page.detachScript(type)` to remove one. Uninstalling the extension removes them too.

The user can read, edit, and delete every one of these scripts in the editor's Code tab.

## Extension state

Use `builder.state` for data that belongs only to the extension.

```ts
await builder.state.set({ query: "icons", page: 2 });
const state = await builder.state.get();
await builder.state.unset("page");
```

State uses browser `localStorage`. Builder scopes it by extension name and limits it to 100 kB.

`state.set` merges fields at the top level. State does not follow the user to another browser.

## Site data

Use `builder.data` to read and write documents on the site. Every method needs the `data.access` capability.

The capability alone grants nothing. The user must also grant access to each doctype, and Builder stores that grant.

```ts
const grant = await builder.data.getAccess("Task");
if (grant.read !== "allowed") {
  const answer = await builder.data.requestAccess("Task", ["read", "write"]);
  if (answer.read !== "allowed") return;
}

const tasks = await builder.data.getList("Task", {
  fields: ["name", "subject", "status"],
  filters: { status: "Open" },
  orderBy: "modified desc",
  pageLength: 20,
});
```

`requestAccess` opens a modal dialog. Call it after the user presses something, never at startup.

Each access in a grant holds one answer: `"allowed"`, `"denied"`, or `"not asked"`. Compare an answer to `"allowed"`, because `"denied"` is a truthy string.

`requestAccess` asks only about each access that is `"not asked"`. It returns without a dialog when every access you name is already allowed or denied. The user can change a denied access in the Extensions panel.

These methods read and write documents:

| Method | Grant | Result |
|---|---|---|
| `data.getList(doctype, options)` | `read` | One page of documents |
| `data.getCount(doctype, filters)` | `read` | How many documents match |
| `data.getDoc(doctype, name)` | `read` | One whole document |
| `data.insert(doctype, doc)` | `write` | The inserted document |
| `data.update(doctype, name, doc)` | `write` | The saved document |
| `data.delete(doctype, name)` | `delete` | Nothing |

`getList` takes `fields`, `filters`, `orFilters`, `orderBy`, `groupBy`, `start`, and `pageLength`. `pageLength` can reach 500. Builder rejects 0.

A call fails with `grant_required` when the access it needs is not allowed. Catch that code and call `requestAccess`. Then read the answer. If the user denied that access before, `requestAccess` returns `"denied"` without a dialog, so tell the user to change it in the Extensions panel. Any other refusal comes from the site, and asking again does not help.

For frappe-ui resources, wire the SDK fetcher once in the entry module:

```ts
import { setConfig } from "frappe-ui";
setConfig("resourceFetcher", builder.data.fetcher);
```

`createListResource` and `createDocumentResource` then work as they do in any Frappe app. The grant rule does not change.

## Doctypes

Use `builder.schema` when the extension needs its own tables. Every method needs the `schema.write` capability.

```ts
const doctype = await builder.schema.createDoctype(
  "Image Tools Preset",
  [
    { fieldname: "preset_name", label: "Preset name", fieldtype: "Data", reqd: true },
    { fieldname: "width", label: "Width", fieldtype: "Int" },
  ],
  { naming: "hash" },
);
```

Builder asks the user before it creates or deletes a doctype. The call fails with `refused` when the user says no.

The user must be a System Manager. Frappe wants create permission on `DocType`, and the extension cannot lift that.

The extension receives a full grant on a doctype it creates, so `data.*` works on it with no second question.

| Method | Behavior |
|---|---|
| `schema.createDoctype(doctype, fields, options)` | Creates a doctype this extension owns |
| `schema.getDoctype(doctype)` | Returns the field list |
| `schema.updateDoctype(doctype, fields)` | Adds fields, and updates fields with a matching `fieldname` |
| `schema.deleteDoctype(doctype)` | Drops the doctype and its table |
| `schema.listDoctypes()` | Returns every doctype this extension made |

`updateDoctype` never removes a field that the call leaves unmentioned. Removing a field drops a column and its data.

Only the extension that created a doctype can update or delete it.

The `naming` value can be `hash`, `autoincrement`, or `prompt`. Builder fixes the naming at creation.

## Builder tokens

Use tokens when a value must reach the published site.

```ts
await builder.tokens.set([
  {
    key: "brand-primary",
    token_name: "Brand Primary",
    type: "Color",
    value: "#2563eb",
    dark_value: "#60a5fa",
    group: "Brand",
  },
]);
```

The token type must be `Color`, `Dimension`, or `Font`. The stable `key` identifies the token inside this extension.

`tokens.set` updates matching keys but does not remove missing keys. Use `tokens.unset(key)` for removal.

Token calls write server records. Await them before showing success.

## Vue slots

The SDK does not include a UI framework. Register a mount adapter once, and every slot then takes a component.

```ts
import builder from "frappe-builder-extension-sdk";
import { vueAdapter } from "frappe-builder-extension-sdk/vue";

builder.use(vueAdapter);

builder.leftPanel.register({
  name: "assets",
  label: "Assets",
  icon: "lucide-images",
  component: () => import("./Panel.vue"),
});
```

A `component` function resolves to a module. The SDK mounts the module's default export with the adapter.

The `props` object becomes the root component props. Dialog and popover calls provide these values.

The adapter unmounts the Vue application when the frame closes.

A module that exports `mount(element, props)` mounts itself. The SDK calls that instead of the adapter, so an extension can mount one slot its own way, or use no framework at all.

```ts
import { defineSlot } from "frappe-builder-extension-sdk/vue";
import Panel from "./Panel.vue";

export const { mount } = defineSlot(Panel);
```

Build the document with Vue, `frappe-ui` components, and Tailwind. Builder uses the same stack, so the frame then matches the editor.

The frame bundles its own Vue, `frappe-ui`, and CSS. It shares nothing with Builder except the SDK.

Use the semantic classes from the `frappe-ui` Tailwind preset, such as `bg-surface-base` and `text-ink-gray-9`. They follow the Builder theme, and a raw color does not.

Use icon names that Builder already renders. An unknown icon name can produce an empty icon.

## Development workflow

1. Create `manifest.json`, `README.md`, `LICENSE`, `vite.config.js`, and `src/main.ts`.
2. Request only the required capabilities.
3. Register actions and surfaces at module scope.
4. Put long-lived work inside `builder.main`.
5. Start the extension with `npm run dev`.
6. Open Builder in developer mode.
7. Select `Load Dev extension` from the main menu.
8. Enter any URL from the extension Vite server.
9. Test each surface in the editor.
10. Run `npm run build` and inspect `dist/main.js` and `dist/manifest.json`.

## Publishing workflow

Set `manifest.v` to the minimum Builder extension protocol the release needs. Run
`npx builder-extension package` after the build. The command writes
`release/<publisher>-<name>-<version>.builderext` after it validates the repository, manifest,
built files, and package limits.

The GitHub release tag must be the manifest version with a `v` prefix. For
example, manifest version `1.2.0` uses tag `v1.2.0`.
Attach the generated package to that release. The SDK template at
`templates/github/workflows/release.yml` automates the build, package checks, release creation,
and attachment for a pushed version tag.

Builder loads one development extension per session. A new development extension replaces the current one.

A page reload removes the development extension. Builder remembers the last development server origin.

Builder ignores unknown requested capabilities during development. Calls that need those capabilities still fail.

Builder permits 100 requests per extension each second. It rejects excess requests with the `rate_limited` error code.

Builder has no install API yet. To install a build on a site, use the script in
[samplePlugin](../samplePlugin/install.py), which writes the files and inserts the
`Builder Extension` record.

Use `builder-extension package` only for release packaging. Builder installation remains a
separate host operation.

## Agent procedure

When a user asks for a Builder component, first identify the user action and the required editor data.

1. Search the target project for an existing extension structure.
2. Reuse its manifest, build setup, components, and naming patterns.
3. Choose a host-rendered surface before you choose a frame.
4. Map each protected SDK call to a manifest capability.
5. Give a surface its action as a function. Use `builder.actions.register` only for an action another frame runs.
6. Add `showWhen` and `enableWhen` rules for selection and read-only state.
7. Use a context subscription only when a rule cannot express the condition.
8. Ask for a doctype grant behind a user action, never at startup.
9. Keep all Builder access behind the public SDK.
10. Keep functions, Vue components, DOM nodes, and class instances inside the frame.
11. Send only plain objects, arrays, strings, numbers, booleans, and null through SDK calls.
12. Build the extension and fix all TypeScript and Vite errors.
13. Test the extension in Builder when a development site is available.

Do not access `window.parent`, Builder stores, or Builder DOM nodes. The sandbox and API do not support those paths.

Do not bundle `frappe-builder-extension-sdk` into extension output. The Vite plugin must keep the SDK external.

Do not register the same visual slot twice. One extension can have one panel, one settings page, one dialog, and one popover slot.

Do not use a surface update to change placement or conditions. Register the item again when those fixed fields must change.

Do not assume that a method exists on an older Builder. An unknown declaration logs a warning and skips that surface.

Keep the feature focused. Add only the surfaces and capabilities that the user request needs.
