/**
 * A plugin from the dev server of its author. It runs only in this session.
 */

import { call } from "frappe-ui";
import { ref } from "vue";
import type { RunnablePlugin } from "./context";
import { loadPlugin, runningPlugins } from "./loader";

/** Only the SDK's Vite plugin serves this path. */
const DESCRIPTOR_PATH = "/__builder-plugin";

const LAST_URL_KEY = "builder-plugin:dev-url";
/** The dev plugin of this tab. A reload loads it again, so an edit that needs a reload keeps it. */
const SESSION_KEY = "builder-plugin:dev-session";
const INSTALL_METHOD = "builder.plugins.development.install_dev_plugin";
const REMOVE_METHOD = "builder.plugins.development.remove_dev_plugin";

export type DevelopmentPlugin = RunnablePlugin & {
	description?: string;
	icon?: string;
	serverOrigin: string;
	readme?: string;
};

/** One at a time. A Vue plugin cannot leave a running app, so a second load needs a reload and a Stop first. */
export const devPlugin = ref<DevelopmentPlugin | null>(null);

export const showDevPluginDialog = ref(false);

/** Both lists have the dev entry under its own name. So the name is the check. */
export const isDevPlugin = (plugin: { name: string }) => devPlugin.value?.name === plugin.name;

export const lastDevUrl = () => localStorage.getItem(LAST_URL_KEY) ?? "";

const read = async (origin: string) => {
	const response = await fetch(`${origin}${DESCRIPTOR_PATH}`).catch(() => {
		throw new Error(`Nothing is answering at ${origin}. Is the dev server running?`);
	});
	const descriptor = response.ok ? await response.json().catch(() => null) : null;
	if (!descriptor?.name) {
		throw new Error(
			`${origin} is not a Builder plugin dev server. Add builderPlugin() to its vite.config.js.`,
		);
	}
	return descriptor;
};

/** The record lets the panel list the plugin. If the site already installed it, it keeps that installation. */
const install = (plugin: string) =>
	// frappe-ui puts the server's own text in `messages`
	call(INSTALL_METHOD, { plugin }).catch((error: { messages?: string[] }) => {
		throw new Error(
			error.messages?.[0] ?? `Builder could not register "${plugin}". Is the site in developer mode?`,
		);
	});

const remove = (plugin: string) =>
	call(REMOVE_METHOD, { plugin }).catch((error: Error) =>
		console.error(`Could not remove development plugin "${plugin}"`, error),
	);

/**
 * Accepts any URL on the dev server. An author pastes the URL from the terminal.
 *
 * Refuses a plugin that this editor already runs. A Vue plugin cannot leave the
 * app, so the dev copy would run beside it.
 */
export const loadDevPlugin = async (url: string): Promise<DevelopmentPlugin> => {
	if (devPlugin.value) throw new Error("Reload the editor to load another dev plugin.");

	const origin = new URL(url.trim()).origin;
	const descriptor = await read(origin);
	if (runningPlugins.has(descriptor.name)) {
		throw new Error(`${descriptor.name} already runs here. Disable it, reload the editor, then load it again.`);
	}
	await install(descriptor.name);

	const plugin: DevelopmentPlugin = {
		name: descriptor.name,
		label: descriptor.label || descriptor.name,
		description: descriptor.description,
		version: descriptor.version,
		serverOrigin: origin,
		readme: descriptor.readme,
		// the dev server serves the source entry. So the path comes from the dev server
		entryUrl: `${origin}${descriptor.entry}`,
		icon: descriptor.icon ? `${origin}${descriptor.icon}` : undefined,
		isDevelopment: true,
	};
	await loadPlugin(plugin);
	localStorage.setItem(LAST_URL_KEY, origin);
	sessionStorage.setItem(SESSION_KEY, origin);
	devPlugin.value = plugin;
	return plugin;
};

/** The Stop button in the Plugins panel. Closing the tab does not call this, so another tab keeps the record. */
export const stopDevPlugin = async () => {
	sessionStorage.removeItem(SESSION_KEY);
	if (devPlugin.value) await remove(devPlugin.value.name);
	devPlugin.value = null;
};

/** After a reload, the dev plugin that this tab ran. A dev server that stopped ends it. */
export const restoreDevPlugin = async () => {
	const origin = sessionStorage.getItem(SESSION_KEY);
	if (!origin) return;
	try {
		await loadDevPlugin(origin);
	} catch (error) {
		sessionStorage.removeItem(SESSION_KEY);
		console.warn(`[builder] the dev plugin at ${origin} did not load again`, error);
	}
};
