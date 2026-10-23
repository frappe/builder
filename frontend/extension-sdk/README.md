# frappe-builder-extension-sdk

The build tooling for trusted Frappe Builder extensions.

A trusted extension is a Vue plugin that the Builder editor loads into its own app. The extension imports `builder`, `vue`, `pinia` and `frappe-ui` from the editor, so this package has no runtime code. It gives an extension project:

- the Vite plugin that builds a package Builder can load, and serves the extension to the editor in development
- the types of the `builder` module
- the `builder-extension create` and `builder-extension package` commands
- a GitHub workflow that publishes each release for Builder Hub

An extension runs with the access of each user who opens the editor. Only a System Manager or a Website Manager can install one.

## Create an extension

```sh
npx frappe-builder-extension-sdk create my-extension
```

The command asks for a name, a publisher, a description, the Builder URL and a copyright holder. Then it writes a project with a sample left panel tab.

## The entry module

The default export of `src/main.ts` is a Vue plugin. Builder calls `install(app, context)` once, before the editor shows:

```ts
import { leftPanelTabs, lucideIcon, useBuilderStore, type ExtensionContext } from "builder";
import type { App } from "vue";
import Panel from "./Panel.vue";

export default {
	install(_app: App, context: ExtensionContext) {
		leftPanelTabs.register({
			name: "seo",
			label: "SEO",
			icon: lucideIcon("lucide-search"),
			component: Panel,
		});
		context.setOpenHandler(() => (useBuilderStore().leftPanelActiveTab = "seo"));
	},
};
```

`builder` gives:

| Export                                                                                          | What it gives                                                                      |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `leftPanelTabs`, `toolbarItems`, `blockContextMenuOptions`, `propertySections`, `settingsItems` | The registries of the editor surfaces. `register` answers with its own unregister. |
| `usePageStore`, `useCanvasStore`, `useBuilderStore`                                             | The editor's stores                                                                |
| `blockController`, `Block`                                                                      | The selected blocks, and the block tree                                            |
| `lucideIcon(name)`                                                                              | Any lucide icon, as a component for an `icon` field                                |
| `StylePropertyControl`, `AttributePropertyControl`, `BasePropertyControl`                       | The controls of the property panel, for an extension's section                     |
| `OptionToggle`, `ColorInput`, `RangeInput`                                                      | The widgets those controls draw instead of a text input                            |

The `context` gives:

| Field                                                  | What it gives                                                                   |
| ------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `name`, `label`, `version`                             | The installed extension                                                         |
| `state.get()`, `state.set(values)`, `state.unset(key)` | Values stored for the user who opens the editor. `set` merges at the top level. |
| `setOpenHandler(handler)`                              | What the Open button in the extension's details page runs                       |

### Every other module

`builder` is the stable entry: Builder keeps it working across releases. Every other module of the editor is reachable too, by its path under `frontend/src/`. A `.ts` module drops its suffix, and a `.vue` module keeps it:

```ts
import usePageStore from "builder/internal/stores/pageStore";
import { getBlockString } from "builder/internal/utils/helpers";
import BlockLayers from "builder/internal/components/BlockLayers.vue";
```

Each one is the editor's own module, so a store or a registry is the same instance the editor uses. These imports carry no promise: a change in Builder can break them, so their types are `any`. When an extension needs something often, ask for it in `builder`.

frappe-ui works with the user's own session. For example, `createListResource` and `call` reach the site's documents and whitelisted methods, and Frappe checks the user's permissions.

### Styles

The SDK puts the extension's styles in the `builder-extension` cascade layer. The editor's own styles sit in no layer, so they win where both style one element. So an extension cannot restyle the editor by accident. To change a style that the editor sets on a shared component, such as a frappe-ui `Button`, use `!important`, for example `!h-8`.

## The manifest

```json
{
	"v": 1,
	"name": "publisher/extension",
	"label": "Extension",
	"description": "What it does.",
	"version": "1.0.0",
	"entry": "main.js",
	"icon": "icon.svg"
}
```

A manifest has no `permissions` field. An extension runs with the access of the user who opens the editor.

## Develop

1. Set `builderUrl` in `vite.config.ts` to the origin that serves Builder.
2. Run `npm run dev`.
3. In the editor, open the **Extensions** tab and choose **Load dev extension**. The site must run in developer mode.
4. Paste the URL that Vite prints.

The dev extension runs until you reload the editor. Vite's hot reload updates its components.

## Package and publish

```sh
npm run build
npm run package -- --tag v1.0.0
```

The package command checks the build against the limits that Builder and Builder Hub use. Then it writes `release/<publisher>-<extension>-<version>.builderext` and prints its SHA-256.

The release workflow does the same on each `v*` tag, and attaches the package to the GitHub release.
