# Extensions

An extension is a Vue plugin that the editor loads into its own app. It has the full access of each user who opens the editor. Install only extensions that you trust.

## Shared modules

An extension imports these modules by their bare names. The editor page has an import map that resolves each name to the editor's own copy. So an extension shares the editor's Vue instance, stores and frappe-ui configuration.

| Import | What it gives |
| --- | --- |
| `builder` | The editor API in [`builder.ts`](./builder.ts): the surface registries, the stores, `blockController` and `Block` |
| `vue` | The editor's Vue |
| `pinia` | The editor's pinia |
| `frappe-ui` | The editor's frappe-ui |

Do not bundle these modules. A second copy of Vue or pinia breaks reactivity and the stores.

## Entry module

The default export of the entry module is a Vue plugin. Register items in `install`:

```js
import { leftPanelTabs } from "builder";
import SeoPanel from "./SeoPanel.vue";

export default {
	install() {
		leftPanelTabs.register({ name: "acme-seo", label: "SEO", icon: "lucide-search", component: SeoPanel });
	},
};
```

## Package

A package is a zip file with `manifest.json` at its root:

```json
{ "name": "acme-seo", "label": "SEO", "version": "1.0.0", "entry": "main.js", "style": "style.css" }
```

- `name` uses lowercase letters, numbers and hyphens.
- `entry` is the ES module that the editor imports.
- `style` is optional. The editor adds it as a stylesheet before it imports the entry.

Build the entry in library mode, with the shared modules as externals:

```js
// vite.config.js
export default {
	build: {
		lib: { entry: "src/main.js", formats: ["es"], fileName: () => "main.js" },
		rollupOptions: { external: ["builder", "vue", "pinia", "frappe-ui"] },
	},
};
```

## Install

1. Open **Builder Extension** in Desk as a System Manager.
2. Attach the package zip and save.

Builder unpacks the package to `/files/builder_extensions/<name>/<checksum>/`. Reload the editor to load the extension. To update an extension, attach a new package and save.

## Development

In developer mode, set **Source** to **Dev Server** and set **Dev Server URL** to the entry module on your Vite dev server, for example `http://localhost:5174/src/main.js`.

Vite rewrites bare imports, but the browser must see the shared modules as bare imports. Add this plugin to the dev server configuration. It resolves each shared module to a small module that re-exports the bare name.

```js
const SHARED = ["builder", "vue", "pinia", "frappe-ui"];
const PREFIX = "/@builder-shared/";
const PORT = 5174;

const sharedImports = {
	name: "builder-shared-imports",
	enforce: "pre",
	resolveId: (id) => (SHARED.includes(id) ? { id: `http://localhost:${PORT}${PREFIX}${id}`, external: true } : undefined),
	configureServer(server) {
		server.middlewares.use((request, response, next) => {
			const name = request.url?.startsWith(PREFIX) && request.url.slice(PREFIX.length);
			if (!SHARED.includes(name)) return next();
			response.setHeader("Content-Type", "text/javascript");
			response.setHeader("Access-Control-Allow-Origin", "*");
			response.end(`export * from "${name}";\n`);
		});
	},
};

export default {
	plugins: [sharedImports],
	optimizeDeps: { exclude: SHARED, noDiscovery: true, include: [] },
	server: { port: PORT, strictPort: true, cors: true },
};
```
