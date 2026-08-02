import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import { transformWithEsbuild } from "vite";

const source = await readFile(new URL("../src/translation.ts", import.meta.url), "utf8");
const transformed = await transformWithEsbuild(source, "translation.ts", {
	format: "cjs",
	target: "es2020",
});

const window = {};
const frappeRequest = async () => ({ message: {} });
const module = { exports: {} };
const warnings = [];
const context = vm.createContext({
	AbortController,
	console: {
		warn(...args) {
			warnings.push(args);
		},
	},
	clearTimeout,
	module,
	exports: module.exports,
	require(specifier) {
		if (specifier === "frappe-ui") return { frappeRequest };
		throw new Error(`Unexpected import: ${specifier}`);
	},
	setTimeout,
	window,
});

new vm.Script(transformed.code, { filename: "translation.ts" }).runInContext(context);

const { __, default: plugin, loadTranslations, setTranslations } = module.exports;
const tests = [
	["falls back to exact English source", () => assert.equal(__("Missing"), "Missing")],
	[
		"uses ordinary dictionary lookup",
		() => {
			setTranslations({ "All Pages": "Alle Seiten" });
			assert.equal(__("All Pages"), "Alle Seiten");
		},
	],
	[
		"uses Source:Context before ordinary lookup",
		() => {
			setTranslations({ Save: "Speichern", "Save:Toolbar": "Sichern" });
			assert.equal(__("Save", [], "Toolbar"), "Sichern");
		},
	],
	[
		"falls back from missing context to source lookup",
		() => {
			setTranslations({ Save: "Speichern" });
			assert.equal(__("Save", [], "Unknown"), "Speichern");
		},
	],
	[
		"falls back from blank context to source lookup",
		() => {
			setTranslations({ Save: "Speichern", "Save:Toolbar": "" });
			assert.equal(__("Save", [], "Toolbar"), "Speichern");
		},
	],
	[
		"falls back from blank translation to English source",
		() => {
			setTranslations({ Save: "" });
			assert.equal(__("Save"), "Save");
		},
	],
	[
		"replaces positional values including numbers",
		() => {
			setTranslations({ "Page {0} has {1} blocks": "Seite {0} hat {1} Blöcke" });
			assert.equal(__("Page {0} has {1} blocks", ["Home", 3]), "Seite Home hat 3 Blöcke");
		},
	],
	[
		"stores a fetched dictionary",
		async () => {
			await loadTranslations(async () => ({ Preview: "Vorschau" }));
			assert.equal(__("Preview"), "Vorschau");
		},
	],
	[
		"installs on Vue globals and window",
		() => {
			const app = { config: { globalProperties: {} } };
			plugin.install(app);
			assert.equal(app.config.globalProperties.__, __);
			assert.equal(window.__, __);
		},
	],
	[
		"keeps English fallback after fetch failure",
		async () => {
			const warningCount = warnings.length;
			setTranslations({ Existing: "Vorhanden" });
			await loadTranslations(async ({ signal }) => {
				assert.equal(signal.aborted, false);
				throw new Error("offline");
			});
			assert.equal(__("Existing"), "Existing");
			assert.equal(warnings.length, warningCount + 1);
		},
	],
	[
		"keeps English fallback without AbortController",
		async () => {
			const warningCount = warnings.length;
			const nativeAbortController = context.AbortController;
			let requestCount = 0;

			setTranslations({ Existing: "Vorhanden" });
			context.AbortController = undefined;
			try {
				await loadTranslations(async () => {
					requestCount += 1;
					return { Existing: "Übersetzt" };
				});
			} finally {
				context.AbortController = nativeAbortController;
			}

			assert.equal(__("Existing"), "Existing");
			assert.equal(warnings.length, warningCount + 1);
			assert.equal(requestCount, 0);
		},
	],
	[
		"times out, aborts, and ignores a late response",
		async () => {
			const warningCount = warnings.length;
			let resolveRequest;
			let requestSignal;
			const lateResponse = new Promise((resolve) => {
				resolveRequest = resolve;
			});

			setTranslations({ Existing: "Vorhanden" });
			await loadTranslations(({ signal }) => {
				requestSignal = signal;
				return lateResponse;
			}, 5);

			assert.equal(requestSignal.aborted, true);
			assert.equal(__("Existing"), "Existing");
			assert.equal(warnings.length, warningCount + 1);

			resolveRequest({ Existing: "Verspätet" });
			await new Promise((resolve) => setTimeout(resolve, 0));
			assert.equal(__("Existing"), "Existing");
		},
	],
];

for (const [name, test] of tests) {
	await test();
	console.log(`ok - ${name}`);
}

console.log(`${tests.length} translation helper tests passed`);
