/**
 * `frappe-builder-extension-sdk/vite`: the build that an extension author runs.
 *
 * This file is plain JavaScript. Vite gives the imports of a config to Node.
 * Node does not remove types from a file under `node_modules`. So a config
 * cannot load a TypeScript plugin from a package.
 *
 * ```js
 * import builderExtension from "frappe-builder-extension-sdk/vite";
 * export default defineConfig({ plugins: [vue(), builderExtension({ builderUrl })] });
 * ```
 */

import fs from "node:fs";
import path from "node:path";
import { parseJson, validateManifest } from "./src/shared/manifest.js";

const MANIFEST = "manifest.json";

/**
 * The editor's own modules. The editor page's import map resolves each bare
 * name to the editor's copy, so an extension shares its Vue, stores and
 * frappe-ui. The build must never bundle them.
 */
export const SHARED_MODULES = ["builder", "vue", "pinia", "frappe-ui"];

/** Every other module of the editor, by its path under `src/`. These carry no promise. */
const INTERNAL_PREFIX = "builder/internal/";

const isShared = (id) => SHARED_MODULES.includes(id) || id.startsWith(INTERNAL_PREFIX);

/**
 * A bare re-export of one shared module. `export *` leaves out `default`, which
 * many internal modules have, so it is passed on as well. A module with no
 * default passes on `undefined`.
 */
const reExport = (name) =>
	[
		`export * from ${JSON.stringify(name)};`,
		`import * as shared from ${JSON.stringify(name)};`,
		"export default shared.default;",
	].join("\n");

/** The dev server answers these paths with a bare re-export of a shared module. */
const SHARED_PATH = "/@builder-shared/";

/** The editor reads this path to learn what the dev server serves. */
const DESCRIPTOR_PATH = "/__builder-extension";

/** The hot reload client of Vite. It loads from the dev server, which serves the entry. */
const HMR_CLIENT = "/@vite/client";

/**
 * The extension shares the editor's Vue. A built editor runs Vue's production
 * build, which has no hot reload runtime, and `@vitejs/plugin-vue` calls that
 * runtime with no check. So in that editor this module gives a runtime that does
 * nothing, and an edit reloads the editor instead. The editor then loads the dev
 * extension again. The entry imports it first, so it runs before any component.
 */
const HMR_FALLBACK_ID = "virtual:builder-hmr-fallback";
const HMR_FALLBACK = `if (import.meta.hot && typeof __VUE_HMR_RUNTIME__ === "undefined") {
	globalThis.__VUE_HMR_RUNTIME__ = { createRecord: () => false, rerender: () => {}, reload: () => {} };
	import.meta.hot.on("vite:beforeUpdate", () => location.reload());
}
`;

/** The port of Vite when the config sets none. */
const DEFAULT_PORT = 5173;

/** The entry of an install. The editor imports it, and it imports its chunks by relative path. */
const OUTPUT_ENTRY = "main.js";

/**
 * The editor's styles sit in no cascade layer, and those beat every layer. So with
 * the extension's styles in one, a class such as `rounded-4` cannot restyle the
 * editor's own elements, whatever order the stylesheets load in.
 */
const STYLE_LAYER = "builder-extension";

/** Vite compiles these to CSS. A special query asks for something else, such as the raw text. */
const STYLESHEET = /\.(css|less|sass|scss|styl|stylus|pcss|postcss|sss)(\?|$)/;
const SPECIAL_QUERY = /[?&](worker|sharedworker|raw|url)\b/;

/**
 * Its own plugin with no `enforce`, so it runs after Vite compiles a stylesheet,
 * and before Vite turns it into a module, in the dev server and in the build.
 */
const layerStyles = () => ({
	name: "builder-extension-style-layer",
	transform(code, id) {
		if (!STYLESHEET.test(id) || SPECIAL_QUERY.test(id)) return;
		return { code: `@layer ${STYLE_LAYER} {\n${code}\n}`, map: null };
	},
});

/** A link, not an inline style, so each `url(...)` in the CSS resolves against the stylesheet. */
const STYLESHEET_LINK = (fileName) =>
	`(() => { const link = document.createElement("link"); link.rel = "stylesheet"; link.href = new URL(${JSON.stringify(fileName)}, import.meta.url).href; document.head.append(link); })();`;

/** One entry. So Rollup sees the full graph, and shared code goes into one chunk. */
const ENTRY_CANDIDATES = ["src/main.ts", "src/main.js"];

/** The editor imports only the entry module. So the entry links the stylesheet, or the extension shows no styles. */
const linkStylesheet = (bundle) => {
	const sheet = Object.values(bundle).find((file) => file.type === "asset" && file.fileName.endsWith(".css"));
	if (!sheet) return;

	const entryChunk = Object.values(bundle).find((file) => file.type === "chunk" && file.isEntry);
	entryChunk.code = `${STYLESHEET_LINK(sheet.fileName)}\n${entryChunk.code}`;
};

const findEntry = (root) => {
	const found = ENTRY_CANDIDATES.find((candidate) => fs.existsSync(path.join(root, candidate)));
	if (found) return path.join(root, found);
	throw new Error(`[builder] no extension entry: expected one of ${ENTRY_CANDIDATES.join(" or ")}`);
};

const readManifest = (root) => {
	const file = path.join(root, MANIFEST);
	if (!fs.existsSync(file)) throw new Error(`[builder] no ${MANIFEST} beside vite.config.js`);
	const source = fs.readFileSync(file, "utf8");
	return { manifest: validateManifest(parseJson(MANIFEST, source)), source };
};

const readReadme = (root) => {
	const file = path.join(root, "README.md");
	return fs.statSync(file, { throwIfNoEntry: false })?.isFile() ? fs.readFileSync(file, "utf8") : undefined;
};

/**
 * @param {{ builderUrl: string }} options `builderUrl` is the origin of the
 * editor. The dev server lets only that origin read its files.
 */
export default function builderExtension({ builderUrl } = {}) {
	if (!builderUrl) {
		throw new Error('[builder] builderExtension() needs "builderUrl", the origin Builder is served on');
	}

	const builderOrigin = new URL(builderUrl).origin;

	let root = process.cwd();
	let entry = "";
	let serving = false;
	let serverOrigin = "";

	/** The dev server path of a file. The editor loads the entry and the icon over HTTP. */
	const servedPath = (file) => `/${path.relative(root, file)}`;

	/** The icon is next to the entry. The install puts it in the root, so the manifest name fits both. */
	const findIcon = (manifest) => (manifest.icon ? path.join(path.dirname(entry), manifest.icon) : "");

	const readIcon = (file) => {
		if (!fs.existsSync(file)) {
			throw new Error(
				`[builder] ${MANIFEST} names ${path.relative(root, file)} as its icon, and it is missing`,
			);
		}
		return fs.readFileSync(file);
	};

	const plugin = {
		name: "builder-extension",
		// run before the resolver of Vite. If not, Vite finds the shared modules on
		// disk, and the extension gets a second copy of Vue
		enforce: "pre",

		config(config, env) {
			root = path.resolve(config.root ?? process.cwd());
			entry = findEntry(root);
			serving = env.command === "serve";
			const port = config.server?.port ?? DEFAULT_PORT;
			serverOrigin =
				config.server?.origin ?? `${config.server?.https ? "https" : "http"}://localhost:${port}`;
			return {
				// a chunk or an asset URL resolves against the module that names it. So
				// the build works under any install URL
				base: "./",
				build: {
					target: "es2020",
					// one stylesheet, because the entry links only one
					cssCodeSplit: false,
					rollupOptions: {
						input: entry,
						preserveEntrySignatures: "strict",
						external: isShared,
						output: {
							entryFileNames: OUTPUT_ENTRY,
							chunkFileNames: "chunks/[name]-[hash].js",
							assetFileNames: "assets/[name]-[hash][extname]",
						},
					},
				},
				// the dev server prebundles with esbuild, which runs no plugin, so a
				// prebundled copy would carry its own Vue. Vite merges this list with the project's
				optimizeDeps: { exclude: SHARED_MODULES },
				server: {
					cors: { origin: [builderOrigin] },
					// an asset URL resolves against the editor page, on the Builder site.
					// So it must name the dev server. `strictPort` keeps the port in the
					// origin correct: Vite stops, and does not try the next port
					port,
					strictPort: true,
					origin: serverOrigin,
				},
			};
		},

		/**
		 * Vite rewrites a bare import to its own copy, but it leaves a full URL as
		 * it is. So in the dev server each shared module resolves to a URL here,
		 * which answers with a bare re-export that the editor's import map resolves.
		 */
		resolveId(id) {
			if (serving && isShared(id)) {
				return { id: `${serverOrigin}${SHARED_PATH}${id}`, external: true };
			}
			if (id === HMR_FALLBACK_ID) return `\0${HMR_FALLBACK_ID}`;
		},

		load(id) {
			if (id === `\0${HMR_FALLBACK_ID}`) return HMR_FALLBACK;
		},

		/**
		 * Loads the hot reload client of Vite. The editor serves its own page, so
		 * Vite cannot add the client to it. `@vitejs/plugin-vue` calls
		 * `import.meta.hot.accept(...)` with no check, so without the client the
		 * first component fails when it loads.
		 */
		transform(code, id) {
			if (!serving || id !== entry) return;
			const imports = [HMR_CLIENT, HMR_FALLBACK_ID].map((id) => `import ${JSON.stringify(id)};`).join("\n");
			return { code: `${imports}\n${code}`, map: null };
		},

		configureServer(server) {
			// answered raw, before Vite's own middleware, so the bare name reaches the browser
			server.middlewares.use(SHARED_PATH, (request, response, next) => {
				const name = request.url?.slice(1);
				if (!isShared(name)) return next();
				response.setHeader("Content-Type", "text/javascript");
				response.setHeader("Access-Control-Allow-Origin", builderOrigin);
				response.end(reExport(name));
			});

			/** The data that "Load dev extension" reads: the identity and the entry. */
			server.middlewares.use(DESCRIPTOR_PATH, (_request, response) => {
				const { manifest } = readManifest(root);
				response.setHeader("Content-Type", "application/json");
				response.setHeader("Access-Control-Allow-Origin", builderOrigin);
				response.end(
					JSON.stringify({
						v: manifest.v,
						name: manifest.name,
						label: manifest.label,
						description: manifest.description,
						version: manifest.version,
						readme: readReadme(root),
						entry: servedPath(entry),
						icon: manifest.icon ? servedPath(findIcon(manifest)) : undefined,
					}),
				);
			});
		},

		/**
		 * Adds the manifest and the icon to the output, and makes the entry link the stylesheet.
		 *
		 * `order: "post"`, because Vite's CSS plugin adds the stylesheet in this same hook.
		 */
		generateBundle: {
			order: "post",
			handler(_options, bundle) {
				const { manifest, source } = readManifest(root);
				this.emitFile({ type: "asset", fileName: MANIFEST, source });

				// the install reads its icon from its root directory
				if (manifest.icon) {
					this.emitFile({ type: "asset", fileName: manifest.icon, source: readIcon(findIcon(manifest)) });
				}

				linkStylesheet(bundle);
			},
		},
	};
	return [plugin, layerStyles()];
}
