/**
 * An extension served from its author's dev server, for this session only.
 *
 * It has no record and no files. The editor asks the dev server what it is
 * serving, and appends one entry to the installed list — which is all the rest of
 * the host reads, so the entry frame, the surfaces, the dispatcher and the
 * teardown need no idea that this one was never installed.
 *
 * A reload drops it, because loading one is a deliberate act and a stale dev
 * extension that fails to load looks like Builder being broken. The last URL is
 * remembered, so nobody retypes it.
 */

import { PERMISSIONS, type Permission, type InstalledExtension } from "frappe-builder-extension-sdk/types";
import { call } from "frappe-ui";
import { ref } from "vue";

/** Served by the build plugin, and by nothing else. */
const DESCRIPTOR_PATH = "/__builder-extension";

const LAST_URL_KEY = "builder-extension:dev-url";
const INSTALL_METHOD = "builder.extensions.development.install_dev_extension";
const REMOVE_METHOD = "/api/method/builder.extensions.development.remove_dev_extension";

export type DevelopmentExtension = InstalledExtension & {
	version: string;
	serverOrigin: string;
	readme?: string;
};

/** One at a time: a second load replaces the first, as one dialog replaces another. */
export const devExtension = ref<DevelopmentExtension | null>(null);

export const showDevExtensionDialog = ref(false);

export const lastDevUrl = () => localStorage.getItem(LAST_URL_KEY) ?? "";

/**
 * A permission this Builder does not know is a version gap, not a fault, so the
 * extension loses that one grant and keeps the rest. Using it is refused by the
 * bridge, as it would be for an installed extension.
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
 * Gives the dev extension an installation of its own, so it passes the same
 * server gate an installed extension does. Without one, every call it makes to
 * Builder is refused.
 *
 * The record answers with what it granted, and that answer is what this entry
 * carries, so the browser gate and the server gate read one list.
 *
 * An extension the site already installed keeps that installation. The
 * server answers with its permissions rather than making a second record.
 */
const install = (extension: string, permissions: Permission[]) =>
	call(INSTALL_METHOD, { extension, permissions }).catch(() => {
		throw new Error(`Builder could not register "${extension}". Is the site in developer mode?`);
	}) as Promise<Permission[]>;

/**
 * Raw `fetch` rather than `call`, because `keepalive` is what lets a request
 * started on `pagehide` outlive the document. Frappe refuses a form POST without
 * the CSRF header, and the browser adds none of its own.
 */
const remove = (extension: InstalledExtension) =>
	fetch(REMOVE_METHOD, {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token ?? "" },
		body: new URLSearchParams({ extension: extension.name }),
		keepalive: true,
	}).catch((error) => console.error(`Could not remove development extension "${extension.name}"`, error));

/** Takes any URL on the dev server, because an author pastes what the terminal printed. */
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
		// the dev server serves the source entry, so the path comes from it
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
