/**
 * `frappe-builder-extension-sdk/vite` — the build an extension author runs.
 *
 * Plain JavaScript on purpose. Vite hands a config's own imports to Node, and
 * Node refuses to strip types from any file under `node_modules`, so a
 * TypeScript plugin cannot be loaded by the config that uses it.
 *
 * ```js
 * import builderExtension from "frappe-builder-extension-sdk/vite";
 * export default defineConfig({ plugins: [vue(), builderExtension({ builderUrl })] });
 * ```
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseJson, validateManifest } from "./src/protocol.js";

const SDK = "frappe-builder-extension-sdk";
const MANIFEST = "manifest.json";

/** Where Builder serves the one SDK instance every frame of an extension shares. */
const SDK_PATH = "/builder_extension_asset/sdk/extension-sdk.js";

/** What the editor reads to learn what this dev server is serving. */
const DESCRIPTOR_PATH = "/__builder-extension";

/** Vite's hot reload client. It resolves against the dev server, which serves the entry. */
const HMR_CLIENT = "/@vite/client";

/** The one file an install holds, and the one the editor reads and posts. */
const OUTPUT_ENTRY = "main.js";

/** Runs in every frame, because every frame imports the entry. */
const STYLE_TAG = (css) =>
	`(() => { const style = document.createElement("style"); style.textContent = ${JSON.stringify(css)}; document.head.append(style); })();`;

/** One entry, so Rollup sees the whole graph and shared code lands in one chunk. */
const ENTRY_CANDIDATES = ["src/main.ts", "src/main.js"];

/** Room for an icon or a cursor, and not for a font. */
const ASSET_INLINE_LIMIT = 64 * 1024;

/**
 * Refuses a build that emitted more than the entry, the manifest and the icon.
 *
 * A frame gets the entry as code, not a URL, so a relative import resolves
 * against nothing and an asset URL points nowhere. Failing here names the file.
 * Failing in a frame prints nothing anywhere.
 */
const assertOneFile = (bundle, manifest) => {
	const allowed = new Set([OUTPUT_ENTRY, MANIFEST, manifest.icon].filter(Boolean));
	const extra = Object.keys(bundle).filter((name) => !allowed.has(name));
	if (!extra.length) return;

	throw new Error(
		`[builder] an extension has to build to one file, and this build also emitted ${extra.join(", ")}. ` +
			`Import a module statically instead of with import(). Drop an asset over ${ASSET_INLINE_LIMIT / 1024} kB, ` +
			"such as a font, and use the one Builder already loads.",
	);
};

/**
 * Moves the stylesheet into the entry.
 *
 * The frame shell is one static document that names no extension, so it can link
 * no stylesheet of one. A built extension's CSS therefore has to carry itself, or
 * every frame paints unstyled.
 */
const foldStylesheets = (bundle) => {
	const sheets = Object.values(bundle).filter(
		(file) => file.type === "asset" && file.fileName.endsWith(".css"),
	);
	if (!sheets.length) return;

	const css = sheets.map((sheet) => sheet.source).join("\n");
	sheets.forEach((sheet) => delete bundle[sheet.fileName]);

	const entryChunk = Object.values(bundle).find((file) => file.type === "chunk" && file.isEntry);
	entryChunk.code = `${STYLE_TAG(css)}\n${entryChunk.code}`;
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
 * @param {{ builderUrl: string }} options `builderUrl` is the origin the editor
 * is opened on. It has no default: the dev server imports the SDK from it by
 * absolute URL, and an origin that is not the one serving the editor loads a
 * second SDK instance, whose frames never connect.
 */
export default function builderExtension({ builderUrl } = {}) {
	if (!builderUrl) {
		throw new Error('[builder] builderExtension() needs "builderUrl", the origin Builder is served on');
	}

	const sdkUrl = `${builderUrl.replace(/\/$/, "")}${SDK_PATH}`;

	let root = process.cwd();
	let entry = "";
	let serving = false;

	/** What the dev server answers for a file, as the editor loads both over HTTP. */
	const servedPath = (file) => `/${path.relative(root, file)}`;

	/**
	 * The icon sits beside the entry, and the install flattens that directory, so
	 * the one name in the manifest holds for the source tree and the install both.
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
		// before Vite's own resolver, or it resolves the SDK to a file on disk and
		// the frame ends up with a second instance of it
		enforce: "pre",

		config(config, env) {
			root = path.resolve(config.root ?? process.cwd());
			entry = findEntry(root);
			serving = env.command === "serve";
			return {
				// nothing built needs this now: a small asset is inlined, and the check
				// below refuses a big one. It stays for the dev server, which serves
				// modules by path rather than as one file
				base: "./",
				// the frame is a modern browser by definition: it runs module scripts
				build: {
					target: "es2020",
					// one stylesheet, because the entry carries the CSS itself. Split CSS
					// also puts a stylesheet in the preload list of every lazy chunk, and
					// the frame then asks for a file this plugin folded into the entry
					cssCodeSplit: false,
					// a small asset goes inside the entry too, for the reason the CSS does:
					// the frame gets code and can fetch nothing.
					//
					// A big one is refused instead. Vite embeds an inlined asset once per
					// reference, so a font named by six @font-face rules lands six times,
					// as base64 that will not compress. Measured: 1.6 MB to 5.6 MB on one
					// sample. A frame also runs inside Builder, which loads its own fonts.
					assetsInlineLimit: ASSET_INLINE_LIMIT,
					rollupOptions: {
						input: entry,
						// never bundled: the frame shell's import map resolves it to the one
						// instance Builder serves. An import map belongs to the document, so
						// it answers a Blob module the way it answers any other
						external: [SDK],
						output: {
							// one file. The editor reads the entry and posts the code to
							// the frame, so a chunk has no URL left to import from
							inlineDynamicImports: true,
							entryFileNames: OUTPUT_ENTRY,
							assetFileNames: "[name]-[hash][extname]",
						},
					},
				},
				server: {
					// an extension frame runs at an opaque origin, so it sends
					// `Origin: null`, and Vite answers such a request with no CORS
					// header at all
					cors: { origin: "*" },
					// the package is installed by a link, so it resolves outside this
					// project and the dev server would refuse to serve it. The project
					// itself has to be named too: this list replaces the default rather
					// than adding to it
					fs: { allow: [root, path.dirname(fileURLToPath(import.meta.url))] },
				},
			};
		},

		/**
		 * Names Builder's own URL for the SDK, rather than leaving the specifier
		 * for the frame's import map.
		 *
		 * Measured: `external: true` alone does not survive a dev server. Vite
		 * rewrites the bare specifier to `/@id/frappe-builder-extension-sdk`, the browser
		 * asks the dev server for it, and the import map never sees it. The frame
		 * would then hold a second SDK instance, with no port and no channel.
		 *
		 * An absolute URL is left alone, and it resolves to the same module the
		 * frame shell already loaded — as long as `builderUrl` is the origin the
		 * editor is open on. That is why the option has no default.
		 */
		resolveId(id) {
			if (serving && id === SDK) return { id: sdkUrl, external: true };
		},

		/**
		 * Loads Vite's hot reload client, which nothing else here would.
		 *
		 * Vite injects it into the HTML it serves. An extension frame is served by
		 * Builder instead, so the client never arrives — and `@vitejs/plugin-vue`
		 * emits `import.meta.hot.accept(...)` with no guard, because it assumes the
		 * client defined it. Without this the first component to load throws while
		 * it evaluates, inside a frame, with nothing printed anywhere.
		 */
		transform(code, id) {
			if (!serving || id !== entry) return;
			return { code: `import ${JSON.stringify(HMR_CLIENT)};\n${code}`, map: null };
		},

		/** What "load development extension" reads: identity, grants, and the entry. */
		configureServer(server) {
			server.middlewares.use(DESCRIPTOR_PATH, (request, response) => {
				const { manifest } = readManifest(root);
				response.setHeader("Content-Type", "application/json");
				// a middleware added here runs before Vite's own, so the CORS setting
				// above has not been applied yet. The editor reads this cross-origin
				response.setHeader("Access-Control-Allow-Origin", "*");
				response.end(
					JSON.stringify({
						v: manifest.v,
						name: manifest.name,
						label: manifest.label,
						description: manifest.description,
						version: manifest.version,
						readme: readReadme(root),
						capabilities: manifest.capabilities ?? [],
						entry: servedPath(entry),
						icon: manifest.icon ? servedPath(findIcon(manifest)) : undefined,
					}),
				);
			});
		},

		/**
		 * Emits the manifest and the icon, folds the stylesheet into the entry, and
		 * refuses a build that is more than one file.
		 *
		 * `order: "post"`, because Vite's own CSS plugin emits that file in this
		 * same hook and this has to run after it.
		 */
		generateBundle: {
			order: "post",
			handler(_options, bundle) {
				const { manifest, source } = readManifest(root);
				this.emitFile({ type: "asset", fileName: MANIFEST, source });

				// the installation reads its icon from the install root, so the file
				// lands there under the name the manifest gave it
				if (manifest.icon) {
					this.emitFile({ type: "asset", fileName: manifest.icon, source: readIcon(findIcon(manifest)) });
				}

				foldStylesheets(bundle);
				assertOneFile(bundle, manifest);
			},
		},
	};
}
