import { devExtension } from "@/extensions/devExtension";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createDocumentResource, createResource, getCachedDocumentResource } from "frappe-ui";
import { computed } from "vue";

const INSTALLATION_DOCTYPE = "Builder Extension";
const SOURCE_URL = "/api/method/builder.extensions.installations.get_extension_source";

type InstallationDocument = {
	extension: string;
	label?: string;
	description?: string;
	enabled: boolean | number;
	checksum?: string;
	granted_permissions?: string;
};

/** The Vue instance a document resource ties its realtime subscription to. Set once, from the editor. */
let resourceVm: unknown;

const grantedPermissions = (value: string | undefined): Permission[] => {
	if (!value) return [];
	return JSON.parse(value) as Permission[];
};

/**
 * One installation's document.
 *
 * `frappe-ui` caches this itself by doctype and name, so calling it again for an
 * installation already loaded returns the same live resource rather than a
 * second copy racing it.
 */
const installationDocument = (installationId: string) =>
	createDocumentResource<InstallationDocument>(
		{
			doctype: INSTALLATION_DOCTYPE,
			name: installationId,
			auto: false,
			realtime: Boolean(resourceVm),
			onError: (error: Error) => console.error("Could not load extension", error),
		},
		resourceVm,
	);

/**
 * Every installation on this site, the disabled and development ones included.
 * The editor mounts the enabled rows.
 */
const installationsResource = createResource<Installation[]>({
	url: "builder.extensions.installations.get_installations",
	// losing this list costs the editor its extensions, never the editor itself
	onError: (error: Error) => console.error("Could not load installations", error),
});

/**
 * Fetch one installation's document into that shared cache.
 *
 * Read it back with `getCachedDocumentResource`, never held here: `toInstalledExtension`
 * only reads that cache, so a fetch never happens as a side effect of a computed.
 */
const loadInstallationDocument = (row: Installation) => {
	void installationDocument(row.installation_id)
		.reload()
		.catch(() => undefined);
};

const toInstalledExtension = (row: Installation): InstalledExtension | null => {
	const document = getCachedDocumentResource<InstallationDocument>(
		INSTALLATION_DOCTYPE,
		row.installation_id,
	)?.doc;
	if (!document || !document.enabled) return null;

	return {
		name: row.name,
		label: document.label ?? row.label ?? row.name,
		description: document.description ?? row.description,
		icon: row.icon,
		checksum: document.checksum,
		permissions: grantedPermissions(document.granted_permissions),
	};
};

/**
 * Every extension this editor runs: the site's installations, plus the one loaded from a
 * dev server this session. A dev extension replaces the installation of the same
 * name, because two entries would give it two frames.
 *
 * A development record never mounts. It has no files, and the browser's own entry
 * runs it.
 */
const installedExtensions = computed<InstalledExtension[]>(() => {
	const installed = (installationsResource.data ?? [])
		.filter((row) => !row.is_development)
		.flatMap((row) => {
			const extension = toInstalledExtension(row);
			return extension ? [extension] : [];
		});
	const development = devExtension.value;
	if (!development) return installed;

	return [...installed.filter((extension) => extension.name !== development.name), development];
});

/** Fetches the list, and the documents of the rows the editor mounts. Call it after every change. */
const loadExtensions = async (vm?: unknown) => {
	if (vm) resourceVm = vm;
	const rows = (await installationsResource.fetch()) ?? [];
	rows.filter((row) => row.enabled && !row.is_development).forEach(loadInstallationDocument);
	return rows;
};

/**
 * The built entry of one installation, as a Blob a frame runs.
 *
 * The editor fetches it, not the frame, because a frame sends no session. A
 * GET, so the browser revalidates by checksum and an unchanged build costs a
 * 304. Fetched once per session and shared by every frame of the extension. A
 * Blob is immutable, so a browser can clone it into a frame as a handle to the
 * same bytes. A string is copied into every frame.
 *
 * The checksum joins the key, so a rebuild is fetched again. A failed fetch is
 * dropped, so a reloaded frame asks rather than replaying the error.
 */
const sources = new Map<string, Promise<Blob>>();

const fetchSource = async (extension: InstalledExtension) => {
	const response = await fetch(`${SOURCE_URL}?${new URLSearchParams({ extension: extension.name })}`);
	if (!response.ok) throw new Error(`Could not read "${extension.name}" (HTTP ${response.status})`);
	return response.blob();
};

const getExtensionSource = (extension: InstalledExtension): Promise<Blob> => {
	const key = `${extension.name}@${extension.checksum ?? ""}`;

	const cached = sources.get(key);
	if (cached) return cached;

	const reading = fetchSource(extension);

	const source = reading.catch((error: Error) => {
		sources.delete(key);
		throw error;
	});
	sources.set(key, source);
	return source;
};

/** One row of the site's installation list. */
type Installation = {
	name: string;
	/** The document's own name, not the extension's. */
	installation_id: string;
	label?: string;
	description?: string;
	icon?: string;
	enabled: boolean;
	/** Made by a dev server load. The browser's own entry runs it, never the row. */
	is_development?: boolean;
};

export { getExtensionSource, INSTALLATION_DOCTYPE, installedExtensions, loadExtensions };
