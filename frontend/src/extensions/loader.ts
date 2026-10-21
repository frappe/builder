import type { App, Plugin } from "vue";
import { reactive } from "vue";
import { createExtensionContext, type RunnableExtension } from "./context";

type LoadedExtension = { extension: RunnableExtension; plugin: Plugin };

/** The app that extensions install into. Set at startup, so a later load reaches the same app. */
let editorApp: App | null = null;

/**
 * The extensions this page runs. A plugin cannot leave a running app, so this
 * only grows until the next reload.
 */
export const runningExtensions = reactive(new Set<string>());

const isPlugin = (value: unknown): value is Plugin =>
	typeof value === "function" || typeof (value as { install?: unknown })?.install === "function";

/**
 * The entry module's default export is a Vue plugin. Its own imports of
 * "builder", "vue", "pinia" and "frappe-ui" resolve through the editor page's
 * import map, and its build links its own stylesheet.
 */
export async function importExtension(extension: RunnableExtension): Promise<Plugin> {
	const module = await import(/* @vite-ignore */ extension.entryUrl);
	if (!isPlugin(module.default)) {
		throw new Error(`${extension.entryUrl} has no default export with an install() function`);
	}
	return module.default;
}

const install = (app: App, { extension, plugin }: LoadedExtension) => {
	app.use(plugin, createExtensionContext(extension));
	runningExtensions.add(extension.name);
};

const report = (extension: RunnableExtension, error: unknown) =>
	console.error(`[builder] the extension "${extension.label}" did not load`, error);

/** An extension that fails to load is skipped, so the editor still starts. */
export async function importExtensions(extensions: RunnableExtension[]): Promise<LoadedExtension[]> {
	const results = await Promise.allSettled(extensions.map(importExtension));
	return results.flatMap((result, index) => {
		if (result.status === "fulfilled") return [{ extension: extensions[index], plugin: result.value }];
		report(extensions[index], result.reason);
		return [];
	});
}

/** At startup, before the first render, so an extension's items show from the start. */
export function installExtensions(app: App, loaded: LoadedExtension[]) {
	editorApp = app;
	for (const entry of loaded) {
		try {
			install(app, entry);
		} catch (error) {
			report(entry.extension, error);
		}
	}
}

/** One extension while the editor runs: a new install, or a dev extension. The registries are reactive, so its items show at once. */
export async function loadExtension(extension: RunnableExtension) {
	if (!editorApp) throw new Error("The editor has not started, so it cannot load an extension");
	install(editorApp, { extension, plugin: await importExtension(extension) });
}
