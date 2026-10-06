/**
 * An extension from the dev server of its author. It runs only in this session.
 *
 * It has no files. The editor asks the dev server what it serves. Then the
 * editor adds one entry to the installed list. The rest of the host reads only
 * that list. So the entry frame, the surfaces, the dispatcher and the teardown
 * do not know that the extension is not installed.
 *
 * A reload removes it. A user must load it on purpose. An old dev extension
 * that fails to load looks like a Builder error. The editor keeps the last URL,
 * so the user does not type it again.
 */

import { PERMISSIONS, type Permission, type InstalledExtension } from "frappe-builder-extension-sdk/types";
import { call } from "frappe-ui";
import { ref } from "vue";

/** Only the build plugin serves this path. */
const DESCRIPTOR_PATH = "/__builder-extension";

const LAST_URL_KEY = "builder-extension:dev-url";
const INSTALL_METHOD = "builder.extensions.registry.install_dev_extension";
const REMOVE_METHOD = "/api/method/builder.extensions.registry.remove_dev_extension";

export type DevelopmentExtension = InstalledExtension & {
	version: string;
	serverOrigin: string;
	readme?: string;
};

/** One at a time. A second load replaces the first. */
export const devExtension = ref<DevelopmentExtension | null>(null);

export const showDevExtensionDialog = ref(false);

export const lastDevUrl = () => localStorage.getItem(LAST_URL_KEY) ?? "";

/** Both lists have the dev entry under its own name. So the name is the check. */
export const isDevExtension = (extension: { name: string }) => devExtension.value?.name === extension.name;

/**
 * An unknown permission shows a version gap, not an error. The extension does
 * not get that permission. It keeps the others. The bridge refuses calls that
 * need it, as for an installed extension.
 */
const grantedFrom = (asked: unknown): Permission[] => {
	const list = Array.isArray(asked) ? asked : [];
	const unknown = list.filter((permission) => !PERMISSIONS.includes(permission));
	if (unknown.length) {
		console.warn(`[builder] this Builder has no ${unknown.join(", ")}, so they are not granted`);
	}
	return list.filter((permission): permission is Permission => PERMISSIONS.includes(permission));
};

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

/**
 * Gives the dev extension its own installation. So it passes the same server
 * gate as an installed extension. Without it, Builder refuses each call.
 *
 * The server returns the granted permissions. This entry keeps that list.
 * So the browser gate and the server gate read the same list. A change in
 * the panel then reaches the browser and the server.
 *
 * If the site already installed the extension, it keeps that installation.
 * The server returns its permissions. It does not make a second record.
 */
const install = (extension: string, permissions: Permission[]) =>
	call(INSTALL_METHOD, { extension, permissions }).catch(() => {
		throw new Error(`Builder could not register "${extension}". Is the site in developer mode?`);
	}) as Promise<Permission[]>;

/** Copies a permission change from the panel to the entry that the browser gate reads. */
export const setDevPermissions = (extension: string, permissions: Permission[]) => {
	if (devExtension.value?.name === extension) devExtension.value.permissions = permissions;
};

/**
 * Uses `fetch`, not `call`. With `keepalive`, a request from `pagehide` can
 * continue after the document closes. Frappe refuses a form POST without the
 * CSRF header. The browser does not add this header.
 */
const remove = (extension: InstalledExtension) =>
	fetch(REMOVE_METHOD, {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token },
		body: new URLSearchParams({ extension: extension.name }),
		keepalive: true,
	}).catch((error) => console.error(`Could not remove development extension "${extension.name}"`, error));

/** Accepts any URL on the dev server. An author pastes the URL from the terminal. */
export const loadDevExtension = async (url: string): Promise<DevelopmentExtension> => {
	const origin = new URL(url.trim()).origin;
	const descriptor = await read(origin);
	if (devExtension.value) await remove(devExtension.value);
	const granted = await install(descriptor.name, grantedFrom(descriptor.permissions));

	localStorage.setItem(LAST_URL_KEY, origin);
	devExtension.value = {
		name: descriptor.name,
		label: descriptor.label || descriptor.name,
		description: descriptor.description,
		version: descriptor.version,
		serverOrigin: origin,
		readme: descriptor.readme,
		// the dev server serves the source entry. So the path comes from the dev server
		entry: `${origin}${descriptor.entry}`,
		icon: descriptor.icon ? `${origin}${descriptor.icon}` : undefined,
		permissions: granted,
	};
	return devExtension.value;
};

export const stopDevExtension = () => {
	if (devExtension.value) void remove(devExtension.value);
	devExtension.value = null;
};

window.addEventListener("pagehide", stopDevExtension);
