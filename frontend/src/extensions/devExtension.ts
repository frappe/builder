/**
 * An extension from the dev server of its author. It runs only in this session.
 *
 * It has no files. The editor asks the dev server what it serves. Then the
 * editor adds one entry to the installed list. The rest of the host reads only
 * that list. So the entry frame, the surfaces, the request handler and the teardown
 * do not know that the extension is not installed.
 *
 * A reload removes it. A user must load it on purpose. An old dev extension
 * that fails to load looks like a Builder error. The editor keeps the last URL,
 * so the user does not type it again.
 *
 * Closing the tab keeps the installation. It belongs to the site, so another
 * tab can run the same extension. The next load refreshes it.
 */

import { PERMISSIONS, type Permission, type InstalledExtension } from "frappe-builder-extension-sdk/types";
import { call } from "frappe-ui";
import { ref } from "vue";

/** Only the build plugin serves this path. */
const DESCRIPTOR_PATH = "/__builder-extension";

const LAST_URL_KEY = "builder-extension:dev-url";
const INSTALL_METHOD = "builder.extensions.development.install_dev_extension";
const REMOVE_METHOD = "builder.extensions.development.remove_dev_extension";

export type DevelopmentExtension = InstalledExtension & {
	version: string;
	serverOrigin: string;
	readme?: string;
};

/** One at a time. A second load replaces the first. */
export const devExtension = ref<DevelopmentExtension | null>(null);

export const showDevExtensionDialog = ref(false);

export const lastDevUrl = () => localStorage.getItem(LAST_URL_KEY) ?? "";

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
 * So the browser gate and the server gate read the same list.
 *
 * If the site already installed the extension, it keeps that installation.
 * The server returns its permissions. It does not make a second record.
 */
const install = (extension: string, permissions: Permission[]) =>
	call(INSTALL_METHOD, { extension, permissions }).catch(() => {
		throw new Error(`Builder could not register "${extension}". Is the site in developer mode?`);
	}) as Promise<Permission[]>;

const remove = (extension: InstalledExtension) =>
	call(REMOVE_METHOD, { extension: extension.name }).catch((error: Error) =>
		console.error(`Could not remove development extension "${extension.name}"`, error),
	);

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
		entryUrl: `${origin}${descriptor.entry}`,
		icon: descriptor.icon ? `${origin}${descriptor.icon}` : undefined,
		permissions: granted,
	};
	return devExtension.value;
};
