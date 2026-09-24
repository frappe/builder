---
name: build-builder-extension
description: Build, run, and install a Frappe Builder extension — toolbar buttons, context menu rows, property sections, left panel tabs, settings pages, dialogs, and popovers, through frappe-builder-extension-sdk. Use when the user asks for a Builder extension, a Builder plugin, or a Builder component, or wants to add a surface to the Builder editor.
---

# Build a Builder extension

An extension adds surfaces to the Frappe Builder editor. It runs in a sandboxed frame and
reaches the editor only through `frappe-builder-extension-sdk`.

Read `references/extension-api.md` before you write any code. It holds the whole API: the
capability list, every surface, the error codes, and the rules the host enforces. This file
holds the workflow only.

## Before you start

Ask the user for two facts, if the request does not carry them:

1. The Builder origin, for example `http://builder.localhost:8080`.
2. What the user does with the feature, and what editor data it needs.

Search the target project for an existing extension first. Reuse its manifest, build setup,
and naming.

## Create the project

Run `npx github:stravo1/frappe-builder-extension-sdk#v0.1.3 create` for a new
project. It creates the manifest, publishing files, TypeScript Vue example, and
development configuration.

When you build the structure manually:

1. Make `manifest.json`, `README.md`, `LICENSE`, `package.json`, `vite.config.ts`,
   and `src/main.ts`.
2. Install the SDK from its release tag:
   `npm install --save-dev github:stravo1/frappe-builder-extension-sdk#v0.1.3`.
3. Add `builderExtension({ builderUrl })` to the Vite plugin list.
4. Add Vue, frappe-ui, and Tailwind when the feature needs a frame. Read the next section.

```js
import vue from "@vitejs/plugin-vue";
import builderExtension from "frappe-builder-extension-sdk/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue(), builderExtension({ builderUrl: "http://builder.localhost:8080" })],
});
```

`builderUrl` must be the origin that serves the editor. Another origin loads a second SDK
instance, and the frame never connects.

## Use Vue, frappe-ui, and Tailwind

Build every frame with Vue, frappe-ui components, and Tailwind. Builder itself uses this
stack, so an extension that uses it looks like part of the editor. Write a plain HTML control
only when frappe-ui has nothing for the job.

The frame bundles its own copy of all three. It shares nothing with Builder except the SDK.

```sh
npm install vue frappe-ui
npm install --save-dev @vitejs/plugin-vue tailwindcss unplugin-icons @iconify-json/lucide
```

Add the frappe-ui preset to `tailwind.config.js`:

```js
import frappeUIPreset from "frappe-ui/tailwind";

export default {
  presets: [frappeUIPreset],
  content: ["./src/**/*.{vue,js,ts}"],
};
```

Make `src/index.css`, and import it from the entry module. The build plugin folds this CSS
into the entry, so every frame paints with it:

```css
@import "frappe-ui/style.css";

@tailwind base;
@tailwind components;
@tailwind utilities;
```

frappe-ui costs two Vite settings. Its components import icons as `~icons/lucide/*`, which
needs a resolver plugin. Vite prebundles a dependency with esbuild, which runs no Vite
plugins, so give the same resolver to both:

```js
import Icons from "unplugin-icons/vite";
import IconsEsbuild from "unplugin-icons/esbuild";

export default defineConfig({
  css: { postcss: { plugins: [tailwindcss({ config: "./tailwind.config.js" })] } },
  plugins: [Icons({ compiler: "vue3" }), vue(), builderExtension({ builderUrl })],
  optimizeDeps: {
    // frappe-ui ships source, and several dependencies of it are CommonJS. A frame
    // that imports one of those unbundled fails on a missing named export.
    include: [
      "frappe-ui > feather-icons",
      "frappe-ui > debug",
      "engine.io-client",
      "interactjs",
      "highlight.js/lib/core",
    ],
    esbuildOptions: { plugins: [IconsEsbuild({ compiler: "vue3" })] },
  },
});
```

Use the semantic classes from the preset, such as `bg-surface-base` and `text-ink-gray-9`.
They follow the Builder theme. A raw color such as `bg-white` does not.

For site data through frappe-ui resources, wire the fetcher once in the entry module:

```js
import { setConfig } from "frappe-ui";
setConfig("resourceFetcher", builder.data.fetcher);
```

It must name this extension's own frappe-ui. Each extension bundles a copy, and the SDK
cannot reach that copy's config.

## Choose the surface

Choose the smallest surface that meets the request:

| The user wants | Use |
|---|---|
| One command | A toolbar button or a context menu row, with an action |
| To edit values on a block | A property section with bound controls |
| A list, a browser, or a form | A left panel tab, a dialog, or a popover |
| Settings for the extension | One settings page |

A host-rendered surface uses Builder's own components. Open a frame only when the feature
needs custom content.

## Write the entry

Put every registration at module scope. Every frame of the extension reads the same module,
and the SDK sends the declarations from the hidden main frame only.

Register an action before the surface that names it. Put startup work in `builder.main`.

Request only the capabilities the code uses. Map each protected call to its capability with
the table in `references/extension-api.md`.

Use the exact version 1 manifest fields: `v`, `name`, `label`, `description`, `version`,
`entry`, optional `icon`, and `capabilities`. Set `entry` to `main.js` and `v` to the
minimum Builder extension protocol the release needs.

## Run it

1. Run `npm run dev` in the extension directory.
2. Open Builder in developer mode.
3. Choose `Load Dev extension` from the main menu.
4. Paste any URL from the Vite dev server.

Builder holds one development extension per session, and a reload drops it.

## Publish it through Builder Hub

1. Update the version and protocol in `manifest.json`.
2. Run `npm run build`.
3. Run `npx builder-extension package`.
4. Create a GitHub release whose tag is the manifest version with a `v` prefix.
5. Attach the generated `release/<publisher>-<name>-<version>.builderext` file.

For automation, copy
`node_modules/frappe-builder-extension-sdk/templates/github/workflows/release.yml` to
`.github/workflows/release.yml`. It supports a pushed version tag and a release
created through GitHub. Both paths validate, build, package, and attach the
release asset.

Submit the public repository to Builder Hub for its first release. Later valid releases
are detected from GitHub and do not need another listing submission.

## Check the result

1. Build the extension and fix every TypeScript and Vite error.
2. Open each surface in the editor.
3. Test the read-only page and a multiple-block selection. Both change what a rule matches.
4. Read the browser console. A skipped surface logs a warning that names the method.

## Rules

Do not reach for `window.parent`, Builder stores, or Builder DOM nodes. The sandbox blocks
them, and the API offers no path to them.

Do not bundle the SDK. The Vite plugin keeps it external, and the frame's import map resolves
it to the one instance Builder serves.

Send only plain data through an SDK call. A function, a Vue component, a DOM node, or a class
instance cannot cross the port.

Register one panel, one settings page, one dialog, and one popover at most. A second one
fails with `already_registered`.

Ask for a doctype grant behind a button the user pressed. `data.requestAccess` opens a modal
dialog, so it must never run at startup.
