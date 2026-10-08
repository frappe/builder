/**
 * The extension from a dev server. It runs only in this session.
 * The editor adds it to the list of extensions. A reload removes it.
 */

import { PERMISSIONS, type Permission, type InstalledExtension } from "frappe-builder-extension-sdk/types";
import { call } from "frappe-ui";
import { ref } from "vue";

/** The build plugin serves this path. */
const DESCRIPTOR_PATH = "/__builder-extension";

const LAST_URL_KEY = "builder-extension:dev-url";
const INSTALL_METHOD = "builder.extensions.development.install_dev_extension";
const REMOVE_METHOD = "builder.extensions.development.remove_dev_extension";

export type DevelopmentExtension = InstalledExtension & {
	version: string;
	serverOrigin: string;
	readme?: string;
};

/** One dev extension at a time. A second load replaces the first. */
export const devExtension = ref<DevelopmentExtension | null>(null);

export const showDevExtensionDialog = ref(false);

export const lastDevUrl = () => localStorage.getItem(LAST_URL_KEY) ?? "";

/** Removes unknown permissions. The extension keeps the other permissions. */
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
 * Adds an installation for the dev extension. Without it, the server refuses each call.
 * Returns the granted permissions. An installed extension keeps its installation.
 */
const install = (extension: string, permissions: Permission[]) =>
	call(INSTALL_METHOD, { extension, permissions }).catch(() => {
		throw new Error(`Builder could not register "${extension}". Is the site in developer mode?`);
	}) as Promise<Permission[]>;

const remove = (extension: InstalledExtension) =>
	call(REMOVE_METHOD, { extension: extension.name }).catch((error: Error) =>
		console.error(`Could not remove development extension "${extension.name}"`, error),
	);

/** Accepts any URL on the dev server. */
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
		// The dev server gives the path of the source entry.
		entryUrl: `${origin}${descriptor.entry}`,
		icon: descriptor.icon ? `${origin}${descriptor.icon}` : undefined,
		permissions: granted,
	};
	return devExtension.value;
};
