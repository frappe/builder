# frappe-builder-extension-sdk

The package a Builder extension author installs. It gives you the types, the Vue
helpers, and the Vite plugin that builds an extension.

## Two halves

The SDK has a runtime half and an author half.

Builder serves the runtime half at `/builder_extension_asset/sdk/extension-sdk.js`.
Every extension frame loads that one module through an import map. Your build
never bundles it.

This package is the author half. It holds the Vite plugin, the Vue helpers, and
the types your editor reads.

## Build an extension

Point Vite at the plugin. Give it the origin that serves Builder.

```js
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import builderExtension from "frappe-builder-extension-sdk/vite";

export default defineConfig({
	plugins: [vue(), builderExtension({ builderUrl: "http://builder.localhost:8000" })],
});
```

The plugin needs a `manifest.json` beside the config, and an entry at
`src/main.js` or `src/main.ts`.

Use the version 1 manifest shape. The build rejects missing and unknown fields.

```json
{
	"v": 1,
	"name": "acme/icons",
	"label": "Icon Library",
	"description": "Add an icon library to Builder.",
	"version": "1.2.0",
	"entry": "main.js",
	"icon": "icon.svg",
	"permissions": ["context.read"]
}
```

A manifest can name an icon, such as `"icon": "icon.svg"`. Put a square SVG of that name beside the
entry.

## Write against the editor

```js
import builder from "frappe-builder-extension-sdk";

builder.toolbar.register({
	name: "say-hello",
	region: "right",
	icon: "lucide-hand",
	action: async () => console.log(await builder.context.get()),
});
```

A Vue slot uses the `/vue` entry. Register the adapter once, and every slot then takes a component.

```js
import { vueAdapter } from "frappe-builder-extension-sdk/vue";

builder.use(vueAdapter);
```

`vue` is an optional peer dependency. Install it only if you write slots in Vue.

## Run it in Builder

1. Turn on developer mode for the site.
2. Start the extension's dev server with `npm run dev`.
3. In the Builder editor, open the command palette and run **Load Dev Extension**.
4. Enter the address the dev server prints.

Builder makes a site installation for the extension and grants what the manifest asks for. Only a
user who manages extensions can load one. The extension runs until you reload the editor.

## Versions

The SDK remains on `0.x` while its authoring API stabilizes. The extension
protocol is versioned separately by the manifest's `v` field.

## License

MIT. Copyright (c) Frappe Technologies Pvt. Ltd. and contributors.
