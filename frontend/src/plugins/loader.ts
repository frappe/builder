import type { App, Plugin } from "vue";
import { reactive } from "vue";
import { collectPluginItems, trackPluginItems, unregisterPluginItems } from "@/utils/createRegistry";
import { preparePluginContext, type PluginContext, type RunnablePlugin } from "./context";

type LoadedPlugin = { plugin: RunnablePlugin; vuePlugin: Plugin };

/** The app that plugins install into. Set at startup, so a later load reaches the same app. */
let editorApp: App | null = null;

/**
 * The plugins this page runs. A Vue plugin cannot leave a running app, so this
 * only grows until the next reload.
 */
export const runningPlugins = reactive(new Set<string>());

/** The entry each running plugin came from. The same URL is the same module, which Vue will not install twice. */
const runningEntries = new Map<string, string>();
const disposers = new Map<string, () => void>();

export const getRunningEntry = (plugin: string) => runningEntries.get(plugin);

const isVuePlugin = (value: unknown): value is Plugin =>
	typeof value === "function" || typeof (value as { install?: unknown })?.install === "function";

/**
 * The entry module's default export is a Vue plugin. Its own imports of
 * "builder", "vue", "pinia" and "frappe-ui" resolve through the editor page's
 * import map, and its build links its own stylesheet.
 */
export async function importPlugin(plugin: RunnablePlugin): Promise<Plugin> {
	const module = await import(/* @vite-ignore */ plugin.entryUrl);
	if (!isVuePlugin(module.default)) {
		throw new Error(`${plugin.entryUrl} has no default export with an install() function`);
	}
	return module.default;
}

// not app.use: it skips a plugin object it has seen, and going back to a release reuses its cached module
const runInstall = (app: App, vuePlugin: Plugin, context: PluginContext) => {
	const install = typeof vuePlugin === "function" ? vuePlugin : vuePlugin.install;
	if (install.constructor.name === "AsyncFunction") throw new Error("Plugin install must be synchronous");
	return install(app, context);
};

const install = (app: App, { plugin, vuePlugin }: LoadedPlugin) => {
	const managed = preparePluginContext(plugin);
	try {
		trackPluginItems(plugin.name, () => runInstall(app, vuePlugin, managed.context));
	} catch (error) {
		managed.dispose();
		throw error;
	}
	disposers.get(plugin.name)?.();
	managed.activate();
	disposers.set(plugin.name, managed.dispose);
	runningPlugins.add(plugin.name);
	runningEntries.set(plugin.name, plugin.entryUrl);
};

const report = (plugin: RunnablePlugin, error: unknown) =>
	console.error(`[builder] the plugin "${plugin.label}" did not load`, error);

/** A plugin that fails to load is skipped, so the editor still starts. */
export async function importPlugins(plugins: RunnablePlugin[]): Promise<LoadedPlugin[]> {
	const results = await Promise.allSettled(plugins.map(importPlugin));
	return results.flatMap((result, index) => {
		if (result.status === "fulfilled") return [{ plugin: plugins[index], vuePlugin: result.value }];
		report(plugins[index], result.reason);
		return [];
	});
}

/** At startup, before the first render, so a plugin's items show from the start. */
export function installPlugins(app: App, loaded: LoadedPlugin[]) {
	editorApp = app;
	for (const entry of loaded) {
		try {
			install(app, entry);
		} catch (error) {
			report(entry.plugin, error);
		}
	}
}

/** One plugin while the editor runs: a new install, or a dev plugin. The registries are reactive, so its items show at once. */
export async function loadPlugin(plugin: RunnablePlugin) {
	install(getEditorApp(), { plugin, vuePlugin: await importPlugin(plugin) });
}

/**
 * A new version of a running plugin. The old module stays in memory, but its
 * registered items go first, so only the new version shows.
 *
 * The import comes first: a version that fails to import leaves the old one running.
 */
export async function replacePlugin(plugin: RunnablePlugin) {
	const vuePlugin = await importPlugin(plugin);
	install(getEditorApp(), { plugin, vuePlugin });
}

/** Takes a plugin's items off the editor. Its module stays in memory until the next reload. */
export function unloadPlugin(plugin: string) {
	disposers.get(plugin)?.();
	disposers.delete(plugin);
	unregisterPluginItems(plugin);
	runningPlugins.delete(plugin);
	runningEntries.delete(plugin);
}

export function getEditorApp(): App {
	if (!editorApp) throw new Error("The editor has not started, so it cannot load a plugin");
	return editorApp;
}

/** Inspect registrations without publishing them into the editor. Call dispose after rendering checks. */
export async function inspectPlugin(plugin: RunnablePlugin) {
	const vuePlugin = await importPlugin(plugin);
	const managed = preparePluginContext(plugin);
	try {
		const entries = collectPluginItems(plugin.name, () =>
			runInstall(getEditorApp(), vuePlugin, managed.context),
		);
		return { entries, dispose: managed.dispose };
	} catch (error) {
		managed.dispose();
		throw error;
	}
}
