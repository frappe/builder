import path from "node:path";

/**
 * Shares the editor's own modules with extensions.
 *
 * Each host module is one more build entry, so it reuses the editor's chunks and
 * its instances of Vue, pinia and frappe-ui. An import map in the editor page
 * gives each module a bare name. An extension that imports "vue" or "builder"
 * then gets the editor's copy, not one of its own.
 */
export const HOST_MODULES = {
	builder: "src/host/builder.ts",
	vue: "src/host/vue.ts",
	pinia: "src/host/pinia.ts",
	"frappe-ui": "src/host/frappe-ui.ts",
};

const entryName = (name) => `host-${name}`;

export default function hostModules({ root }) {
	let base = "/";

	const buildInput = () => ({
		index: path.resolve(root, "index.html"),
		...Object.fromEntries(
			Object.entries(HOST_MODULES).map(([name, file]) => [entryName(name), path.resolve(root, file)]),
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
			Object.entries(HOST_MODULES).map(([name, file]) => [
				name,
				bundle ? builtUrl(bundle, file) : `/${file}`,
			]),
		),
	});

	return {
		name: "builder-host-modules",
		config(_config, { command }) {
			if (command !== "build") return;
			// Vite drops the exports of an app entry by default, and a host module exists only for its exports
			return { build: { rollupOptions: { input: buildInput(), preserveEntrySignatures: "strict" } } };
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
