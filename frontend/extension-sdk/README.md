# frappe-builder-extension-sdk

The package a Builder extension author installs. It gives you the types, the Vue
helpers, and the Vite plugin that builds an extension.

## Install

```sh
npm install --save-dev github:stravo1/frappe-builder-extension-sdk#v0.1.3
```

## Create an extension

Run the scaffolder directly from GitHub. The SDK does not need to be published
to npm.

```sh
npx github:stravo1/frappe-builder-extension-sdk#v0.1.3 create
```

It creates a TypeScript Vue extension with frappe-ui, Tailwind, a development
server, an example toolbar popover, release automation, and a Git repository.
It does not install dependencies. Run the commands it prints when it finishes.

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
	"permissions": ["page.edit"]
}
```

A manifest can name an icon, such as `"icon": "icon.svg"`. Put a square SVG of that name beside the
entry. Builder draws it beside the extension in the Extensions panel.

Put a `README.md` in the extension directory. The installer stores it on the installation, and the
Extensions panel shows it.

The panel also lists every permission the manifest asks for, and the user can turn one off. A
permission the user turned off is refused the way one you never asked for is.

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

In the right region, Builder's own buttons always stay at the right end. `before` and `after` place
your button among the extension buttons only.

A Vue slot uses the `/vue` entry. Register the adapter once, and every slot then takes a component.

```js
import { vueAdapter, useBuilderContext } from "frappe-builder-extension-sdk/vue";

builder.use(vueAdapter);
builder.popover.register({ component: () => import("./Popover.vue") });
```

`vue` is an optional peer dependency. Install it only if you write slots in Vue.

## Run it in Builder

1. Turn on developer mode for the site.
2. Start the extension's dev server with `npm run dev`.
3. In the Builder editor, open the command palette and run **Load Dev Extension**.
4. Enter the address the dev server prints.

Builder makes a site installation for the extension and grants what the manifest asks for. Only a
user who manages extensions can load one. The extension runs until you reload the editor.

The dev server stays on one port, 5173 by default. If that port is in use, the dev server stops.
To run a second extension, set `server.port` in its `vite.config.js`.

The plugin sets the asset URLs to `http://localhost:<port>`, or `https://` when `server.https` is
set. If a plugin turns on HTTPS for you, such as `@vitejs/plugin-basic-ssl`, set `server.origin`.

## Package a release

Builder Hub reads `manifest.json`, `README.md`, and `LICENSE` from the repository root.
Each release manifest declares its required Builder extension protocol in `v`.

Build, then create the release package:

```sh
npm run build
npx builder-extension package
```

The command validates the repository, manifest, built files, and package limits. A
package contains only `manifest.json`, `main.js`, and the optional SVG icon. The command
writes `release/acme-icons-1.2.0.builderext` and prints its size and SHA-256.

The packager and the Hub install do not accept `chunks/` or `assets/` yet. Until they do, a
build that splits its code, or has CSS, cannot be packaged. It still runs from a dev server.

Create a GitHub release whose tag is the manifest version with a `v` prefix. For
example, manifest version `1.2.0` uses tag `v1.2.0`. Copy the workflow shipped at
`templates/github/workflows/release.yml` to `.github/workflows/release.yml`. It
supports both pushed tags and releases created on GitHub.

The first release and repository need Builder Hub review. For a later release, update
`manifest.json`, commit it, and push the exact version tag. Builder Hub detects and
validates the new GitHub release without another listing submission.

## Agent skill

The package ships a skill for Claude Code and other agents. It holds the workflow, and
the whole API as a reference file.

```sh
cp -R node_modules/frappe-builder-extension-sdk/skills/build-builder-extension ~/.claude/skills/
```

Then ask the agent for a Builder extension.

## Versions

The SDK remains on `0.x` while its authoring API stabilizes. The extension
protocol is versioned separately by the manifest's `v` field.

## License

MIT. Copyright (c) Frappe Technologies Pvt. Ltd. and contributors.
