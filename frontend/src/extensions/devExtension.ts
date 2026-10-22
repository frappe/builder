/**
 * An extension from the dev server of its author. It runs only in this session.
 */

import { call } from "frappe-ui";
import { ref } from "vue";
import type { RunnableExtension } from "./context";
import { loadExtension, runningExtensions } from "./loader";

/** Only the SDK's Vite plugin serves this path. */
const DESCRIPTOR_PATH = "/__builder-extension";

const LAST_URL_KEY = "builder-extension:dev-url";
/** The dev extension of this tab. A reload loads it again, so an edit that needs a reload keeps it. */
const SESSION_KEY = "builder-extension:dev";
const INSTALL_METHOD = "builder.extensions.development.install_dev_extension";
const REMOVE_METHOD = "builder.extensions.development.remove_dev_extension";

export type DevelopmentExtension = RunnableExtension & {
	description?: string;
	icon?: string;
	serverOrigin: string;
	readme?: string;
};

/** One at a time. A plugin cannot leave a running app, so a second load needs a reload and a Stop first. */
export const devExtension = ref<DevelopmentExtension | null>(null);

export const showDevExtensionDialog = ref(false);

/** Both lists have the dev entry under its own name. So the name is the check. */
export const isDevExtension = (extension: { name: string }) => devExtension.value?.name === extension.name;

export const lastDevUrl = () => localStorage.getItem(LAST_URL_KEY) ?? "";

type DevSession = { origin: string; name: string };

const readSession = (): DevSession | null => JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? "null");

const saveSession = (session: DevSession) => sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));

/** The extension that this tab runs from a dev server. Startup skips its installed copy, so one copy runs. */
export const getDevSessionExtension = () => (window.is_developer_mode ? readSession()?.name : undefined);

const read = async (origin: string) => {
	const response = await fetch(`${origin}${DESCRIPTOR_PATH}`).catch(() => {
		throw new Error(`Nothing is answering at ${origin}. Is the dev server running?`);
	});
	const descriptor = response.ok ? await response.json().catch(() => null) : null;
	if (!descriptor?.name) {
		throw new Error(
			`${origin} is not a Builder extension dev server. Add builderExtension() to its vite.config.js.`,
		);
	}
	return descriptor;
};

/** The record lets the panel list the extension. If the site already installed it, it keeps that installation. */
const install = (extension: string) =>
	call(INSTALL_METHOD, { extension }).catch(() => {
		throw new Error(`Builder could not register "${extension}". Is the site in developer mode?`);
	});

const remove = (extension: string) =>
	call(REMOVE_METHOD, { extension }).catch((error: Error) =>
		console.error(`Could not remove development extension "${extension}"`, error),
	);

/**
 * Accepts any URL on the dev server. An author pastes the URL from the terminal.
 *
 * Answers null when the installed copy of the extension runs. A plugin cannot
 * leave the app, so the dev copy takes its place after a reload.
 */
export const loadDevExtension = async (url: string): Promise<DevelopmentExtension | null> => {
	if (devExtension.value) throw new Error("Reload the editor to load another dev extension.");

	const origin = new URL(url.trim()).origin;
	const descriptor = await read(origin);
	await install(descriptor.name);
	if (runningExtensions.has(descriptor.name)) {
		localStorage.setItem(LAST_URL_KEY, origin);
		saveSession({ origin, name: descriptor.name });
		return null;
	}

	const extension: DevelopmentExtension = {
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
	await loadExtension(extension);
	localStorage.setItem(LAST_URL_KEY, origin);
	saveSession({ origin, name: descriptor.name });
	devExtension.value = extension;
	return extension;
};

/** The Stop button in the Extensions panel. Closing the tab does not call this, so another tab keeps the record. */
export const stopDevExtension = async () => {
	sessionStorage.removeItem(SESSION_KEY);
	if (devExtension.value) await remove(devExtension.value.name);
	devExtension.value = null;
};

/** After a reload, the dev extension that this tab ran. A dev server that stopped ends it. */
export const restoreDevExtension = async () => {
	const session = readSession();
	if (!session) return;
	try {
		await loadDevExtension(session.origin);
	} catch (error) {
		sessionStorage.removeItem(SESSION_KEY);
		console.warn(`[builder] the dev extension at ${session.origin} did not load again`, error);
	}
};
