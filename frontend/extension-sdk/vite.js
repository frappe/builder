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
import { fileURLToPath } from "node:url";
import { parseJson, validateManifest } from "./src/shared/manifest.js";

const SDK = "frappe-builder-extension-sdk";
const MANIFEST = "manifest.json";

/** The URL where Builder serves the one SDK copy that all frames of an extension share. */
const SDK_PATH = "/builder_extension_asset/sdk/extension-sdk.js";

/** The editor reads this path to learn what the dev server serves. */
const DESCRIPTOR_PATH = "/__builder-extension";

/** The hot reload client of Vite. It loads from the dev server, which serves the entry. */
const HMR_CLIENT = "/@vite/client";

/** The port of Vite when the config sets none. */
const DEFAULT_PORT = 5173;

/** The entry of an install. A frame imports it from Builder, and it imports its chunks by relative path. */
const OUTPUT_ENTRY = "main.js";

/**
 * Runs in each frame, because each frame imports the entry. A link, not an
 * inline style, so each `url(...)` in the CSS resolves against the stylesheet.
 */
const STYLESHEET_LINK = (fileName) =>
	`(() => { const link = document.createElement("link"); link.rel = "stylesheet"; link.href = new URL(${JSON.stringify(fileName)}, import.meta.url).href; document.head.append(link); })();`;

/** One entry. So Rollup sees the full graph, and shared code goes into one chunk. */
const ENTRY_CANDIDATES = ["src/main.ts", "src/main.js"];

/**
 * Makes the entry link the stylesheet.
 *
 * The frame shell is one static document. It names no extension. So it
 * cannot link the stylesheet of an extension. The entry must link it. If
 * not, each frame shows no styles.
 */
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
 * editor. It has no default. The dev server imports the SDK from this origin
 * by absolute URL. A different origin loads a second SDK copy. The frames of
 * that copy do not connect.
 */
export default function builderExtension({ builderUrl } = {}) {
	if (!builderUrl) {
		throw new Error('[builder] builderExtension() needs "builderUrl", the origin Builder is served on');
	}

	const builderOrigin = new URL(builderUrl).origin;
	const sdkUrl = `${builderOrigin}${SDK_PATH}`;

	let root = process.cwd();
	let entry = "";
	let serving = false;

	/** The dev server path of a file. The editor loads the entry and the icon over HTTP. */
	const servedPath = (file) => `/${path.relative(root, file)}`;

	/**
	 * The icon is next to the entry. The install puts all files in one directory.
	 * So the name in the manifest is correct for the source and for the install.
	 */
	const findIcon = (manifest) => (manifest.icon ? path.join(path.dirname(entry), manifest.icon) : "");

	const readIcon = (file) => {
		if (!fs.existsSync(file)) {
			throw new Error(
				`[builder] ${MANIFEST} names ${path.relative(root, file)} as its icon, and it is missing`,
			);
		}
		return fs.readFileSync(file);
	};

	return {
		name: "builder-extension",
		// run before the resolver of Vite. If not, Vite finds the SDK on disk,
		// and the frame gets a second copy of it
		enforce: "pre",

		config(config, env) {
			root = path.resolve(config.root ?? process.cwd());
			entry = findEntry(root);
			serving = env.command === "serve";
			const port = config.server?.port ?? DEFAULT_PORT;
			return {
				// a chunk or an asset URL resolves against the module that names it. So
				// the build works under any install URL
				base: "./",
				// the frame runs module scripts. So it is always a modern browser
				build: {
					target: "es2020",
					// one stylesheet, because the entry links only one
					cssCodeSplit: false,
					rollupOptions: {
						input: entry,
						// the build never includes the SDK. The import map of the frame
						// shell points it to the one copy that Builder serves, for the
						// entry and for every chunk
						external: [SDK],
						output: {
							entryFileNames: OUTPUT_ENTRY,
							chunkFileNames: "chunks/[name]-[hash].js",
							assetFileNames: "assets/[name]-[hash][extname]",
						},
					},
				},
				server: {
					// an extension frame has an opaque origin. It sends `Origin: null`.
					// Any site can send `null` from a sandboxed frame, so this list
					// stops a plain fetch, but the source files are not private
					cors: { origin: [builderOrigin, "null"] },
					// an asset URL resolves against the frame document, on the Builder
					// site. So it must name the dev server. `strictPort` keeps the port
					// in the origin correct: Vite stops, and does not try the next port
					port,
					strictPort: true,
					origin: config.server?.origin ?? `${config.server?.https ? "https" : "http"}://localhost:${port}`,
					// the package is installed by a link, so it is outside this project.
					// Without this, the dev server does not serve it. The project must
					// also be in the list, because this list replaces the default list
					fs: { allow: [root, path.dirname(fileURLToPath(import.meta.url))] },
				},
			};
		},

		/**
		 * Changes the SDK import to the Builder URL. Without this, the import
		 * map of the frame gets the import.
		 *
		 * `external: true` alone does not work on a dev server. Vite changes the
		 * package name to `/@id/frappe-builder-extension-sdk`. The browser then
		 * asks the dev server for it, and the import map never sees it. The frame
		 * then has a second SDK copy, with no port and no channel.
		 *
		 * Vite does not change an absolute URL. It gives the same module that the
		 * frame shell loaded, if `builderUrl` is the origin of the editor. That is
		 * why the option has no default.
		 */
		resolveId(id) {
			if (serving && id === SDK) return { id: sdkUrl, external: true };
		},

		/**
		 * Loads the hot reload client of Vite. No other code loads it.
		 *
		 * Vite adds the client to the HTML that it serves. Builder serves the
		 * extension frame, so the client does not load. `@vitejs/plugin-vue` calls
		 * `import.meta.hot.accept(...)` with no check. It expects the client to
		 * set it. Without this, the first component fails when it loads. The
		 * error is inside a frame, so no message shows.
		 */
		transform(code, id) {
			if (!serving || id !== entry) return;
			return { code: `import ${JSON.stringify(HMR_CLIENT)};\n${code}`, map: null };
		},

		/** The data that "load development extension" reads: the identity, the permissions and the entry. */
		configureServer(server) {
			server.middlewares.use(DESCRIPTOR_PATH, (request, response) => {
				const { manifest } = readManifest(root);
				response.setHeader("Content-Type", "application/json");
				// this middleware runs before the middleware of Vite. So the CORS
				// setting above does not apply yet. Only the editor reads this, never a frame
				response.setHeader("Access-Control-Allow-Origin", builderOrigin);
				response.end(
					JSON.stringify({
						v: manifest.v,
						name: manifest.name,
						label: manifest.label,
						description: manifest.description,
						version: manifest.version,
						readme: readReadme(root),
						permissions: manifest.permissions ?? [],
						entry: servedPath(entry),
						icon: manifest.icon ? servedPath(findIcon(manifest)) : undefined,
					}),
				);
			});
		},

		/**
		 * Adds the manifest and the icon to the output. Makes the entry link the
		 * stylesheet.
		 *
		 * `order: "post"` is necessary. The CSS plugin of Vite adds the stylesheet
		 * in this same hook. This code must run after it.
		 */
		generateBundle: {
			order: "post",
			handler(_options, bundle) {
				const { manifest, source } = readManifest(root);
				this.emitFile({ type: "asset", fileName: MANIFEST, source });

				// the install reads its icon from its root directory. So the file
				// goes there, with the name from the manifest
				if (manifest.icon) {
					this.emitFile({ type: "asset", fileName: manifest.icon, source: readIcon(findIcon(manifest)) });
				}

				linkStylesheet(bundle);
			},
		},
	};
}
