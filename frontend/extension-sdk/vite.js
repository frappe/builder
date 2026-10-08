/**
 * `frappe-builder-extension-sdk/vite`: the build plugin for extensions. It is plain JavaScript for Node.
 * Usage: `plugins: [vue(), builderExtension({ builderUrl })]`.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseJson, validateManifest } from "./src/shared/manifest.js";

const SDK = "frappe-builder-extension-sdk";
const MANIFEST = "manifest.json";

/** The URL where Builder serves the SDK. */
const SDK_PATH = "/builder_extension_asset/sdk/extension-sdk.js";

/** The editor reads this path to learn what the dev server serves. */
const DESCRIPTOR_PATH = "/__builder-extension";

/** The hot reload client of Vite. */
const HMR_CLIENT = "/@vite/client";

/** The Vite port if the config sets none. */
const DEFAULT_PORT = 5173;

/** The entry file of the build. It imports its chunks by relative path. */
const OUTPUT_ENTRY = "main.js";

/** Adds a stylesheet link in each frame. A link lets each `url(...)` in the CSS resolve against the stylesheet. */
const STYLESHEET_LINK = (fileName) =>
	`(() => { const link = document.createElement("link"); link.rel = "stylesheet"; link.href = new URL(${JSON.stringify(fileName)}, import.meta.url).href; document.head.append(link); })();`;

/** One entry. So Rollup puts shared code into one chunk. */
const ENTRY_CANDIDATES = ["src/main.ts", "src/main.js"];

/** Makes the entry link the stylesheet. The frame page does not know the extension. */
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
 * @param {{ builderUrl: string }} options `builderUrl` is the origin of the editor. It has no default.
 * The dev server imports the SDK from it. A different origin gives a second SDK that does not connect.
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

	/** The dev server path of a file. */
	const servedPath = (file) => `/${path.relative(root, file)}`;

	/** The icon is next to the entry. The install keeps all files in one folder, so the name stays correct. */
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
		// Run before the Vite resolver. If not, Vite finds the SDK on disk and adds a second copy.
		enforce: "pre",

		config(config, env) {
			root = path.resolve(config.root ?? process.cwd());
			entry = findEntry(root);
			serving = env.command === "serve";
			const port = config.server?.port ?? DEFAULT_PORT;
			return {
				// Relative URLs. So the build works at any install URL.
				base: "./",
				// The frame runs module scripts. So the browser is always modern.
				build: {
					target: "es2020",
					// One stylesheet, because the entry links only one.
					cssCodeSplit: false,
					rollupOptions: {
						input: entry,
						// Do not include the SDK. The import map of the frame gives it.
						external: [SDK],
						output: {
							entryFileNames: OUTPUT_ENTRY,
							chunkFileNames: "chunks/[name]-[hash].js",
							assetFileNames: "assets/[name]-[hash][extname]",
						},
					},
				},
				server: {
					// An extension frame sends `Origin: null`. This list stops a plain fetch.
					// The source files are not private.
					cors: { origin: [builderOrigin, "null"] },
					// Asset URLs must name the dev server. `strictPort` keeps the port in the origin correct.
					port,
					strictPort: true,
					origin: config.server?.origin ?? `${config.server?.https ? "https" : "http"}://localhost:${port}`,
					// The package is linked, so it is outside the project. Allow both folders.
					// This list replaces the default list.
					fs: { allow: [root, path.dirname(fileURLToPath(import.meta.url))] },
				},
			};
		},

		/**
		 * Changes the SDK import to the Builder URL on the dev server.
		 * If not, Vite serves a second SDK copy with no port.
		 */
		resolveId(id) {
			if (serving && id === SDK) return { id: sdkUrl, external: true };
		},

		/**
		 * Loads the Vite hot reload client. Builder serves the frame page, so Vite cannot add it.
		 * `@vitejs/plugin-vue` needs the client. Without it, the first component fails.
		 */
		transform(code, id) {
			if (!serving || id !== entry) return;
			return { code: `import ${JSON.stringify(HMR_CLIENT)};\n${code}`, map: null };
		},

		/** The data that the editor reads to load a dev extension. */
		configureServer(server) {
			server.middlewares.use(DESCRIPTOR_PATH, (request, response) => {
				const { manifest } = readManifest(root);
				response.setHeader("Content-Type", "application/json");
				// This runs before the Vite CORS setting. Only the editor reads it.
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
		 * Adds the manifest and the icon to the output, and links the stylesheet.
		 * `order: "post"` is necessary. The Vite CSS plugin adds the stylesheet in this hook.
		 */
		generateBundle: {
			order: "post",
			handler(_options, bundle) {
				const { manifest, source } = readManifest(root);
				this.emitFile({ type: "asset", fileName: MANIFEST, source });

				// The install reads the icon from its root folder.
				if (manifest.icon) {
					this.emitFile({ type: "asset", fileName: manifest.icon, source: readIcon(findIcon(manifest)) });
				}

				linkStylesheet(bundle);
			},
		},
	};
}
