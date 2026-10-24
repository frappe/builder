import fs from "node:fs";
import path from "node:path";

/**
 * Shares the editor's own modules with plugins.
 *
 * Each host module is one more build entry, so it reuses the editor's chunks and
 * its instances of Vue, pinia and frappe-ui. An import map in the editor page
 * gives each module a bare name. A plugin that imports "vue" or "builder"
 * then gets the editor's copy, not one of its own.
 */
export const HOST_MODULES = {
	builder: "src/host/builder.ts",
	vue: "src/host/vue.ts",
	pinia: "src/host/pinia.ts",
	"frappe-ui": "src/host/frappe-ui.ts",
};

/**
 * Every other module of the editor, as `builder/internal/<path>`. These carry no
 * promise: a change in Builder can break a plugin that imports one.
 *
 * `main.ts` would start a second app, and the host modules have names of their own.
 */
const INTERNAL_PREFIX = "builder/internal/";
const SOURCE_FILE = /\.(ts|vue)$/;
const NOT_A_MODULE = /(\.test\.ts|\.d\.ts)$/;
const NOT_INTERNAL = new Set(["src/main.ts"]);

/** Set while the plugin runs its own baseline build, which leaves the internal modules out. */
const BASELINE_BUILD = "BUILDER_HOST_MODULES_BASELINE";

/** A `.ts` module drops its suffix, as an import names it. A `.vue` module keeps it. */
const internalName = (file) => INTERNAL_PREFIX + file.slice("src/".length).replace(/\.ts$/, "");

const internalModules = (root) =>
	Object.fromEntries(
		fs
			.readdirSync(path.join(root, "src"), { recursive: true })
			.map((file) => path.posix.join("src", file.split(path.sep).join("/")))
			.filter((file) => SOURCE_FILE.test(file) && !NOT_A_MODULE.test(file))
			.filter((file) => !NOT_INTERNAL.has(file) && !file.startsWith("src/host/"))
			.sort()
			.map((file) => [internalName(file), file]),
	);

/** A Rollup entry name, unique per module, that makes a readable file name. */
const entryName = (name) => `host/${name.replace(/[^a-zA-Z0-9/_-]/g, "_")}`;

/**
 * Where the editor's own build puts each module, by module id.
 *
 * An entry per internal module would split the editor into many more chunks, and
 * it would load several times as many files at startup. Pinning each module to
 * the chunk this build puts it in keeps the editor's split as it is. Each internal
 * entry then becomes a small facade that re-exports from those chunks.
 */
const getBaselineChunks = async (configFile) => {
	const { build } = await import("vite");
	process.env[BASELINE_BUILD] = "1";
	try {
		const result = await build({ configFile, logLevel: "silent", build: { write: false } });
		const chunks = (Array.isArray(result) ? result : [result])
			.flatMap((output) => output.output)
			.filter((item) => item.type === "chunk");
		// one group per chunk, so each name must be unique
		return new Map(
			chunks.flatMap((chunk, index) => chunk.moduleIds.map((id) => [id, `${chunk.name}~${index}`])),
		);
	} finally {
		delete process.env[BASELINE_BUILD];
	}
};

export default function hostModules({ root, configFile }) {
	let base = "/";
	const isBaseline = Boolean(process.env[BASELINE_BUILD]);
	const modules = isBaseline ? HOST_MODULES : { ...HOST_MODULES, ...internalModules(root) };

	const buildInput = () => ({
		index: path.resolve(root, "index.html"),
		...Object.fromEntries(
			Object.entries(modules).map(([name, file]) => [entryName(name), path.resolve(root, file)]),
		),
	});

	const builtUrl = (bundle, file) => {
		const entry = path.resolve(root, file);
		const chunk = Object.values(bundle).find(
			(output) => output.type === "chunk" && output.facadeModuleId === entry,
		);
		if (!chunk) throw new Error(`[builder-host-modules] the build has no chunk for ${file}`);
		return `${base}${chunk.fileName}`;
	};

	const importMap = (bundle) => ({
		imports: Object.fromEntries(
			Object.entries(modules).map(([name, file]) => [name, bundle ? builtUrl(bundle, file) : `/${file}`]),
		),
	});

	const pinnedChunks = async () => {
		const chunkOf = await getBaselineChunks(configFile);
		return {
			groups: [{ name: (id) => chunkOf.get(id) ?? null }],
			// a module goes to its baseline chunk, and its imports stay where they are
			includeDependenciesRecursively: false,
		};
	};

	return {
		name: "builder-host-modules",
		async config(_config, { command }) {
			if (command !== "build") return;
			return {
				build: {
					rollupOptions: {
						input: buildInput(),
						// Vite drops the exports of an app entry by default, and a host module exists only
						// for its exports. "allow-extension" lets a pinned chunk carry them, beside its own
						preserveEntrySignatures: "allow-extension",
						output: isBaseline ? {} : { codeSplitting: await pinnedChunks() },
					},
				},
			};
		},
		configResolved(config) {
			base = config.base;
		},
		transformIndexHtml: {
			order: "post",
			// before every module script, or the browser ignores the map. Indented, so the
			// page's Jinja never meets a "}}"
			handler: (_html, { bundle }) => [
				{
					tag: "script",
					attrs: { type: "importmap" },
					children: JSON.stringify(importMap(bundle), null, "\t"),
					injectTo: "head-prepend",
				},
			],
		},
	};
}
